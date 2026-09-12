import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from sklearn.cluster import KMeans
import torch
from torch import nn
from torch.nn import functional as F

from aligned_embedllm import legacy_area
from audit.estimators import cluster_table


def map_network(dimensions, clusters):
    return nn.Sequential(nn.BatchNorm1d(dimensions, eps=.001, momentum=.01),
        nn.Linear(dimensions, 128), nn.BatchNorm1d(128, eps=.001, momentum=.01), nn.ReLU(),
        nn.Linear(128, 128), nn.BatchNorm1d(128, eps=.001, momentum=.01), nn.ReLU(),
        nn.Linear(128, clusters), nn.Softmax(dim=1))


def learned_map(features, quality, labels, clusters, seed):
    torch.manual_seed(seed)
    model = map_network(features.shape[1], clusters).to(features.device)
    for layer in model:
        if isinstance(layer, nn.Linear):
            nn.init.xavier_uniform_(layer.weight)
            nn.init.zeros_(layer.bias)
    _, profile = cluster_table(labels, quality, torch.arange(clusters, device=features.device), clusters, quality.mean(0, keepdim=True))
    optimizer = torch.optim.Adam(model.parameters(), lr=.005, eps=1e-7)
    generator = torch.Generator(device=features.device).manual_seed(seed)
    losses = []
    with torch.enable_grad():
        for _ in range(5):
            total = 0.
            for ids in torch.randperm(len(features), generator=generator, device=features.device).split(64):
                prediction = (model(features[ids]) @ profile).clamp(1e-7, 1-1e-7)
                loss = F.binary_cross_entropy(prediction, quality[ids])
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()
                total += loss.item()*len(ids)
            losses.append(total/len(features))
    model.eval()
    return model, profile, losses


def sparse_predictions(assignment, ids, quality, target, clusters, soft=None):
    prediction, profile = cluster_table(assignment[ids], quality, assignment[target], clusters, quality.mean(0, keepdim=True))
    return prediction if soft is None else soft @ profile


@torch.no_grad()
def run(capture, output):
    started = time.monotonic()
    torch.set_num_threads(4)
    device = torch.device('cpu')
    output.mkdir(parents=True, exist_ok=False)
    metadata = json.loads((capture / 'manifest.json').read_text())
    encoder = metadata['encoder']
    embedding_path = Path(f'/data/embedllm_emb_{encoder}.npy')
    assert hashlib.sha256(embedding_path.read_bytes()).hexdigest() == metadata['input_sha256'][str(embedding_path)]
    a = {k: torch.tensor(v, device=device) for k, v in np.load(capture / 'protocol.npz').items()}
    x = torch.tensor(np.load(embedding_path), device=device).float()
    scores = torch.tensor(np.load('/data/embedllm_scores.npy'), device=device).float()
    train, val, test, models = a['train_q'], a['val_q'], a['test_q'], a['train_models']
    train_x = x[train].cpu().numpy()
    val_x = x[val].cpu().numpy()
    train_y = scores[train][:, models]
    tuning = []
    best = {'uniroute_kmeans_paper': None, 'uniroute_learnedmap_paper': None}
    grid = list(range(3, len(val)//50+1))
    for k in grid:
        estimator = KMeans(n_clusters=k, n_init=10, max_iter=300, random_state=170000+k).fit(train_x)
        train_labels = torch.tensor(estimator.labels_, device=device)
        val_labels = torch.tensor(estimator.predict(val_x), device=device)
        hard, _ = cluster_table(train_labels, train_y, val_labels, k, train_y.mean(0, keepdim=True))
        network, profile, losses = learned_map(x[train], train_y, train_labels, k, 180000+k)
        learned = network(x[val]) @ profile
        row = dict(k=k, kmeans_area=legacy_area(hard, scores[val][:, models], a['costs'][models]),
            learnedmap_area=legacy_area(learned, scores[val][:, models], a['costs'][models]), training_loss=losses)
        tuning.append(row)
        for name, metric in [('uniroute_kmeans_paper', 'kmeans_area'), ('uniroute_learnedmap_paper', 'learnedmap_area')]:
            if best[name] is None or row[metric] > best[name]['area']:
                best[name] = dict(k=k, area=row[metric], estimator=estimator, network=network if 'learnedmap' in name else None)
        print(json.dumps(row), flush=True)
    selection = {name: dict(k=value['k'], validation_area=value['area']) for name, value in best.items()}
    (output / 'tuning.json').write_text(json.dumps(dict(grid=grid, selection=selection, candidates=tuning), indent=2)+'\n')
    predictions = {}
    for name, value in best.items():
        assignment = torch.tensor(value['estimator'].predict(x.cpu().numpy()), device=device)
        np.save(output / f'{name}_centers.npy', value['estimator'].cluster_centers_)
        network = value['network']
        soft = network(x[test]) if network is not None else None
        if network is not None:
            torch.save(network.state_dict(), output / 'learnedmap.pt')
        for budget in (60, 200, 500, len(val)):
            label = f'k={budget}' if budget != len(val) else f'full-val({budget})'
            for seed in (range(5) if budget != len(val) else range(1)):
                observations = torch.tensor(np.load(capture / f'{seed}_observations_{label}.npy'), device=device)
                columns = []
                for model, ids in zip(a['test_models'], observations):
                    columns.append(sparse_predictions(assignment, ids, scores[ids, model][:, None], test, value['k'], soft))
                prediction = torch.cat(columns, 1)
                np.save(output / f'{seed}_{name}_{budget}.npy', prediction.cpu().numpy())
                predictions[name, budget, seed] = legacy_area(prediction, a['true_test'], a['costs'][a['test_models']])
    rows = [dict(method=name, budget=budget, seed=seed, area=area) for (name, budget, seed), area in predictions.items()]
    result = dict(encoder=encoder, selection=selection, records=rows, seconds=time.monotonic()-started,
        paper='https://arxiv.org/html/2502.08773v2', cluster_grid=grid, keras_hyperparameters_matched=True, execution_device='cpu',
        differences=['BGE instead of Gecko', 'PyTorch instead of Keras', '62 training models and 12 reserved tuning models instead of 74 training models',
            'One historical split instead of 400 random splits', 'Legacy shared Area instead of paper cost-domain integral',
            'K-means defaults and random seeds are explicit local choices', 'Empty clusters use observed model mean'],
        protocol_sha256=hashlib.sha256((capture / 'protocol.npz').read_bytes()).hexdigest())
    (output / 'report.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(selection), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('capture', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    run(args.capture, args.output)
