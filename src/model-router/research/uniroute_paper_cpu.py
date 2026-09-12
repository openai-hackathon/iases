import argparse
import hashlib
import json
from pathlib import Path
import platform
import time
import unicodedata

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
import torch
from torch import nn
from torch.nn import functional as F

from aligned_embedllm import hierarchy, historical_prior, historical_strength
from audit.estimators import cluster_table, empirical_strength, fit_clusters
from paper_metrics import paper_metrics
from research40.serving import fit_router, predict_router
from uniroute_aligned import learned_map, map_network


ROOT = Path(__file__).resolve().parents[1]


def text_unique_ids(rows):
    unique = {}
    for prompt_id, key in sorted(rows):
        unique.setdefault(key, prompt_id)
    return np.array(sorted(unique.values()), dtype=np.int64)


def load_data(dataset, cleaning='consistent'):
    if cleaning not in ('consistent', 'text'):
        raise ValueError(cleaning)
    source = ROOT/'data'
    if dataset == 'embedllm':
        paths = [source/'embedllm_scores.npy', source/'embedllm_emb_bge.npy']
        arrays = dict(np.load(source/'aligned_embedllm_v1/bge/protocol.npz'))
        costs = arrays['costs'].astype(np.float64)
        scores, x = [np.load(p) for p in paths]
        eligible = set(np.load(ROOT/'results/iclr_cpu_completion/consistent_prompt_ids.npy').tolist())
        identity = json.loads((ROOT/'results/prompt_identity_cpu/prompt_identity.json').read_text())
        ids = text_unique_ids((row['prompt_id'], row['normalized_sha256']) for row in identity
            if cleaning == 'text' or row['prompt_id'] in eligible)
        audit = dict(rule='Exclude any conflicting model label; keep lowest ID per normalized exact text', rows=len(scores), eligible=len(ids))
    else:
        paths = [source/'rb_scores.npy', source/'emb_0shot.npy']
        candidates = sorted((source/'hf/datasets--withmartian--routerbench/snapshots').glob('*/routerbench_0shot.pkl'))
        assert len(candidates) == 1, candidates
        paths.append(candidates[0])
        frame = pd.read_pickle(candidates[0])
        names = [c.removesuffix('|total_cost') for c in frame if c.endswith('|total_cost') and c.removesuffix('|total_cost') in frame]
        scores, x = [np.load(p) for p in paths[:2]]
        np.testing.assert_array_equal(scores, frame[names].to_numpy(dtype=np.float32).clip(0, 1))
        costs = frame[[name+'|total_cost' for name in names]].mean().to_numpy(dtype=np.float64)
        assert 'prompt' in frame, list(frame.columns)
        identity = [' '.join(unicodedata.normalize('NFKC', str(value)).casefold().split()) for value in frame['prompt']]
        groups = {}
        for i, text in enumerate(identity):
            groups.setdefault(text, []).append(i)
        consistent = [group[0] for group in groups.values() if np.equal(scores[group], scores[group[0]]).all()]
        ids = text_unique_ids(enumerate(identity)) if cleaning == 'text' else np.array(sorted(consistent))
        audit = dict(rule='Keep first row per normalized exact prompt only when all model labels agree', rows=len(scores),
            eligible=len(ids), duplicate_groups=sum(len(v)>1 for v in groups.values()), conflicting_groups=len(groups)-len(consistent),
            models=names, source_columns=list(frame.columns), source_snapshot=candidates[0].parent.name)
    if cleaning == 'text':
        audit['rule'] = 'Keep lowest prompt ID per normalized exact text; ignore all model scores for eligibility'
        audit['eligible'] = len(ids)
    assert scores.shape[0] == x.shape[0] and scores.shape[1] == len(costs)
    assert np.isfinite(scores).all() and np.isfinite(x).all() and np.isfinite(costs).all() and (costs>0).all()
    assert ((scores >= 0) & (scores <= 1)).all()
    values, counts = np.unique(scores, return_counts=True)
    audit['nonbinary_cells'] = int((~np.isin(scores, [0, 1])).sum())
    audit['score_values'] = {str(value): int(count) for value, count in zip(values, counts)}
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    return torch.from_numpy(x).float(), torch.from_numpy(scores).float(), costs, ids, audit, hashes


def metric(prediction, quality, costs):
    return paper_metrics(prediction.detach().numpy(), quality.numpy(), costs)


def tune(x, scores, train, val, models, costs, output):
    train_y, val_y = scores[train][:, models], scores[val][:, models]
    complete = ['tuning.json','uniroute_kmeans_centers.npy','uniroute_learnedmap_centers.npy','learnedmap.pt']
    if all((output/name).exists() for name in complete):
        best = json.loads((output/'tuning.json').read_text())['selected']
        for name in ('uniroute_kmeans','uniroute_learnedmap'):
            best[name]['centers'] = torch.from_numpy(np.load(output/f'{name}_centers.npy'))
        network = map_network(x.shape[1],best['uniroute_learnedmap']['k'])
        network.load_state_dict(torch.load(output/'learnedmap.pt',weights_only=True))
        best['uniroute_learnedmap']['network'] = network.eval()
        return best
    checkpoint = output/'tuning_progress.pt'
    state = torch.load(checkpoint,weights_only=False) if checkpoint.exists() else dict(
        best={name: None for name in ('uniroute_kmeans','uniroute_learnedmap','knn')}, rows=[], knn_rows=[])
    best, rows = state['best'], state['rows']
    for k in range(3+len(rows), len(val)//50+1):
        estimator = KMeans(n_clusters=k, n_init=10, max_iter=300, random_state=170000+k).fit(x[train].numpy())
        labels = torch.from_numpy(estimator.labels_).long()
        target = torch.from_numpy(estimator.predict(x[val].numpy())).long()
        hard, _ = cluster_table(labels, train_y, target, k, train_y.mean(0, keepdim=True))
        network, profile, losses = learned_map(x[train], train_y, labels, k, 180000+k)
        learned = network(x[val]) @ profile
        row = dict(k=k, kmeans=metric(hard, val_y, costs[models])['area'],
            learnedmap=metric(learned, val_y, costs[models])['area'], loss=losses)
        for name, key in [('uniroute_kmeans', 'kmeans'), ('uniroute_learnedmap', 'learnedmap')]:
            if best[name] is None or row[key] > best[name]['area']:
                best[name] = dict(k=k, area=row[key], centers=torch.from_numpy(estimator.cluster_centers_), network=network)
        rows.append(row)
        torch.save(state, checkpoint.with_suffix('.tmp'))
        checkpoint.with_suffix('.tmp').replace(checkpoint)
        if k%10 == 0:
            print(json.dumps(dict(phase='cluster_tuning', **row)), flush=True)
    limit = len(val)//3
    neighbors = torch.cat([torch.cdist(x[ids], x[train]).topk(limit, largest=False).indices for ids in val.split(256)])
    sums = state.get('sums', torch.zeros(len(val), len(models)))
    knn_rows = state['knn_rows']
    start = knn_rows[-1]['k']+1 if knn_rows else 1
    for k in range(start, limit+1):
        sums += train_y[neighbors[:, k-1]]
        if k < 5:
            continue
        area = metric(sums/k, val_y, costs[models])['area']
        knn_rows.append(dict(k=k, area=area))
        if best['knn'] is None or area > best['knn']['area']:
            best['knn'] = dict(k=k, area=area)
        if k%100 == 0:
            state['sums'] = sums
            torch.save(state, checkpoint.with_suffix('.tmp'))
            checkpoint.with_suffix('.tmp').replace(checkpoint)
    selected = {name: {key: value[key] for key in ('k', 'area')} for name, value in best.items()}
    for name in ('uniroute_kmeans', 'uniroute_learnedmap'):
        np.save(output/f'{name}_centers.npy', best[name]['centers'].numpy())
    torch.save(best['uniroute_learnedmap']['network'].state_dict(), output/'learnedmap.pt')
    (output/'tuning.json').write_text(json.dumps(dict(clusters=rows, knn=knn_rows, selected=selected), indent=2)+'\n')
    print(json.dumps(dict(phase='selected', **selected)), flush=True)
    return best


def clairvoyant(x, scores, train, val, models, costs, seed, output):
    torch.manual_seed(seed)
    model = nn.Sequential(nn.Linear(x.shape[1], 100), nn.ReLU(), nn.Linear(100, 100), nn.ReLU(), nn.Linear(100, len(models)))
    if (output/'clairvoyant.pt').exists() and (output/'clairvoyant_tuning.json').exists():
        model.load_state_dict(torch.load(output/'clairvoyant.pt',weights_only=True))
        return model.eval()
    optimizer = torch.optim.Adam(model.parameters(), lr=.001)
    ids = torch.cat([train, val])
    target = scores[:, models]
    best, best_state, rows = -np.inf, None, []
    with torch.enable_grad():
        for epoch in range(30):
            model.train()
            for batch in ids[torch.randperm(len(ids))].split(64):
                loss = F.binary_cross_entropy_with_logits(model(x[batch]), target[batch])
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()
            model.eval()
            with torch.no_grad():
                area = metric(model(x[val]).sigmoid(), target[val], costs[models])['area']
            rows.append(dict(epoch=epoch+1, validation_area=area))
            if area > best:
                best = area
                best_state = {key: value.detach().clone() for key, value in model.state_dict().items()}
    model.load_state_dict(best_state)
    torch.save(best_state, output/'clairvoyant.pt')
    (output/'clairvoyant_tuning.json').write_text(json.dumps(rows, indent=2)+'\n')
    return model.eval()


def estimates(x, scores, train, observed, target, train_models, models, costs, labels, parents, reference, strengths, shared):
    y = scores[observed][:, models]
    columns = {name: [] for name in ('hiershrink', 'prior', 'prior_only', 'single20', 'single100', 'no_gate')}
    families = torch.zeros(scores.shape[1], dtype=torch.long)
    for i, model in enumerate(models):
        quality = y[:, i:i+1]
        prior, fitted = historical_prior(reference, observed, quality, target, train_models, model, families,
            torch.from_numpy(costs).float(), metadata=False)
        residual = quality-fitted
        scale = (3*(1-residual.square().mean()/(quality-quality.mean()).square().mean().clamp_min(1e-3)).clamp(-1, 1)).exp()
        adjusted = {k: value*scale for k, value in strengths.items()}
        columns['hiershrink'].append(hierarchy(labels, observed, quality, target, strengths, parents))
        columns['prior'].append(prior+hierarchy(labels, observed, residual, target, adjusted, parents))
        columns['prior_only'].append(prior)
        columns['no_gate'].append(prior+hierarchy(labels, observed, residual, target, strengths, parents))
        for k in (20, 100):
            correction, _ = cluster_table(labels[k][observed], residual, labels[k][target], k, residual.mean(0, keepdim=True), adjusted[k])
            columns[f'single{k}'].append(prior+correction)
    result = {name: torch.cat(value, 1) for name, value in columns.items()}
    features = dict(reference=reference[observed], labels={k: value[observed] for k, value in labels.items()})
    target_features = dict(reference=reference[target], labels={k: value[target] for k, value in labels.items()})
    state = fit_router('flat_split_uniform', x[observed], y, features, None, shared)
    result['flat'] = predict_router(state, x[target], target_features)
    result['zero'] = y.mean(0, keepdim=True).expand(len(target), -1)
    return result


@torch.no_grad()
def run(dataset, seed, cleaning='consistent'):
    started = time.monotonic()
    torch.set_num_threads(4)
    version = 'uniroute_paper_cpu_v2' if cleaning == 'consistent' else 'uniroute_text_cpu_v1'
    output = ROOT/'results'/version.removesuffix('_v1')/dataset/str(seed)
    if (output/'report.json').exists():
        print(json.dumps(dict(phase='already_complete',dataset=dataset,seed=seed)),flush=True)
        return
    x, scores, costs, eligible, audit, hashes = load_data(dataset, cleaning)
    output.mkdir(parents=True, exist_ok=True)
    generator = np.random.default_rng(seed)
    permutation = generator.permutation(eligible)
    ntrain, nval = int(.6*len(eligible)), int((.1 if dataset == 'embedllm' else .01)*len(eligible))
    train, val, test = [torch.from_numpy(a) for a in np.split(permutation, [ntrain, ntrain+nval])]
    model_order = generator.permutation(scores.shape[1])
    count = int((2/3 if dataset == 'embedllm' else .5)*len(model_order))
    train_models, models = [torch.from_numpy(a) for a in np.split(model_order, [count])]
    order = val[torch.from_numpy(generator.permutation(len(val)))]
    budgets = [k for k in (20, 40, 60, 100, 150, 200, 300, 400, 500, 750, 1000, 1500, 2000) if k < len(val)]+[len(val)]
    np.savez_compressed(output/'protocol.npz', train=train.numpy(), val=val.numpy(), test=test.numpy(),
        train_models=train_models.numpy(), test_models=models.numpy(), observed=order.numpy(), costs=costs,
        quality=scores[test][:, models].numpy(), static_quality=scores[test][:, train_models].numpy())
    source = Path(__file__).parent
    protocol = dict(dataset=dataset, seed=seed, device='cpu', precision='float32', cpu_threads=4, platform=platform.platform(),
        budgets=budgets, source_audit=audit, inputs_sha256=hashes, split='Random prompts 60/10/30 or 60/1/39; random models 2/3 or 1/2 construction',
        observation='One nested permutation per split; identical IDs for all models and methods',
        metric='Exact clipped-score policy breakpoints; feasible cost domain [min,max]; area50 integrates to 0.5*max with full-domain denominator',
        prior='No family or parameter metadata; existing fixed temperature and shrinkage recipe',
        source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in
            [source/name for name in ('uniroute_paper_cpu.py','paper_metrics.py','uniroute_aligned.py','aligned_embedllm.py','research40/exact_frontier.py','research40/serving.py')]})
    if (output/'protocol.json').exists():
        previous = json.loads((output/'protocol.json').read_text())
        history = previous.get('execution_source_history',[previous['source_sha256']])
        if history[-1] != protocol['source_sha256']:
            history.append(protocol['source_sha256'])
        protocol['execution_source_history'] = history
    (output/'protocol.json').write_text(json.dumps(protocol, indent=2)+'\n')
    selected = tune(x, scores, train, val, train_models, costs, output)
    oracle = clairvoyant(x, scores, train, val, models, costs, seed, output)
    normalized = F.normalize(x, dim=1)
    labels = {}
    for k in (20, 100):
        centers = fit_clusters(normalized[train], k, seed+k)
        labels[k] = (normalized @ centers.T).argmax(1)
        np.save(output/f'hierarchy_centers_{k}.npy', centers.numpy())
    parents = torch.tensor([torch.bincount(labels[20][train][labels[100][train] == c], minlength=20).argmax() for c in range(100)])
    reference = torch.zeros(len(x), len(train_models))
    reference[train] = scores[train][:, train_models]
    for ids in torch.cat([val, test]).split(256):
        neighbors = (normalized[ids] @ normalized[train].T).topk(30, dim=1).indices
        reference[ids] = scores[train][:, train_models][neighbors].mean(1)
    strengths = historical_strength(labels, train, scores[train][:, train_models])
    shared = dict(strength={k: empirical_strength(labels[k][train], scores[train][:, train_models], k, scores[train][:, train_models].mean(0)) for k in labels})
    assignment = {name: torch.cat([torch.cdist(x[ids], selected[name]['centers']).argmin(1) for ids in torch.arange(len(x)).split(1024)]) for name in ('uniroute_kmeans','uniroute_learnedmap')}
    soft = selected['uniroute_learnedmap']['network'](x[test])
    neighbors = torch.cat([torch.cdist(x[ids], x[order]).argsort(dim=1, stable=True) for ids in test.split(256)])
    oracle_prediction = oracle(x[test]).sigmoid()
    records, curves = [], {}
    for budget in budgets:
        observed = order[:budget]
        prediction = estimates(normalized, scores, train, observed, test, train_models, models, costs, labels, parents, reference, strengths, shared)
        quality = scores[observed][:, models]
        for name in assignment:
            k = selected[name]['k']
            hard, profile = cluster_table(assignment[name][observed], quality, assignment[name][test], k, quality.mean(0, keepdim=True))
            prediction[name] = hard if name == 'uniroute_kmeans' else soft @ profile
        usable = neighbors < budget
        ranks = usable.cumsum(1)
        mask = usable & (ranks <= min(selected['knn']['k'], budget))
        chosen = neighbors[mask].reshape(len(test), -1)
        prediction['knn'] = scores[order[chosen]][:, :, models].mean(1)
        prediction['clairvoyant'] = oracle_prediction
        for name, value in prediction.items():
            result = metric(value, scores[test][:, models], costs[models])
            records.append(dict(dataset=dataset, seed=seed, budget=budget, method=name,
                **{key: result[key] for key in ('area','area50','qnc','reached_best','peak_accuracy','brier','best_single_accuracy','best_single_cost')}))
            curves[f'{budget}/{name}'] = result
        np.savez_compressed(output/f'predictions_{budget}.npz', **{name: value.numpy() for name, value in prediction.items()})
        print(json.dumps(dict(phase='evaluated', budget=budget, elapsed=time.monotonic()-started)), flush=True)
    static = estimates(normalized, scores, train, order, test, train_models, train_models, costs, labels, parents, reference, strengths, shared)
    for name in assignment:
        k = selected[name]['k']
        hard, profile = cluster_table(assignment[name][order], scores[order][:,train_models], assignment[name][test], k, scores[order][:,train_models].mean(0,keepdim=True))
        static[name] = hard if name == 'uniroute_kmeans' else soft @ profile
    static['knn'] = scores[order[neighbors[:, :selected['knn']['k']]]][:,:,train_models].mean(1)
    np.savez_compressed(output/'static_predictions.npz', **{name: value.numpy() for name, value in static.items()})
    for name, value in static.items():
        result = metric(value, scores[test][:,train_models], costs[train_models])
        records.append(dict(dataset=dataset, seed=seed, budget='static', method=name,
            **{key: result[key] for key in ('area','area50','qnc','reached_best','peak_accuracy','brier','best_single_accuracy','best_single_cost')}))
        curves[f'static/{name}'] = result
    (output/'curves.json').write_text(json.dumps(curves)+'\n')
    (output/'report.json').write_text(json.dumps(dict(protocol=protocol, records=records, seconds=time.monotonic()-started), indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('dataset', choices=('embedllm','routerbench'))
    parser.add_argument('seed', type=int)
    parser.add_argument('--inspect', action='store_true')
    parser.add_argument('--cleaning', choices=('consistent', 'text'), default='consistent')
    args = parser.parse_args()
    if args.inspect:
        x, scores, costs, ids, audit, hashes = load_data(args.dataset, args.cleaning)
        print(json.dumps(dict(embeddings=list(x.shape), scores=list(scores.shape), costs=costs.tolist(), audit=audit, hashes=hashes)), flush=True)
    else:
        run(args.dataset, args.seed, args.cleaning)
