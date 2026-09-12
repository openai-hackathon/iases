import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import torch
from torch.nn import functional as F

from audit.estimators import cluster_table, empirical_strength
from research40.kernels import RidgeSolver
from research40.serving import fit_router, predict_router


ALPHAS = (.01, .1, 1., 10., 100.)


def legacy_area(predictions, quality, costs):
    best_cost = costs[quality.mean(0).argmax()]
    points = []
    for lam in [0.] + [10 ** e for e in np.linspace(-6, 1, 40)]:
        chosen = (predictions-lam*costs[None]).argmax(1)
        points.append(((costs[chosen].mean()/best_cost).item(), quality.gather(1, chosen[:, None]).mean().item()))
    points.sort()
    x, y = np.asarray(points).T
    x = np.concatenate([[0.], x.clip(0, 1), [1.]])
    y = np.concatenate([[y[0]], y, [y[-1]]])
    return float(np.trapz(y, x))


def hierarchy(labels, ids, y, target, strength, parents, query_parent=False):
    mean = y.mean(0, keepdim=True)
    _, coarse = cluster_table(labels[20][ids], y, torch.arange(20, device=y.device), 20, mean, strength[20])
    if query_parent:
        fine_sum = torch.zeros(100, 1, device=y.device).index_add_(0, labels[100][ids], y)
        count = torch.bincount(labels[100][ids], minlength=100)[:, None]
        lam = strength[100]
        if lam.ndim:
            lam = lam[labels[100][target]][:, None]
        return (fine_sum[labels[100][target]]+lam*coarse[labels[20][target]])/(count[labels[100][target]]+lam)
    prediction, _ = cluster_table(labels[100][ids], y, labels[100][target], 100, mean, strength[100], coarse[parents])
    return prediction


def historical_strength(labels, train, reference):
    result = {}
    for k, assignment in labels.items():
        sums = torch.zeros(k, reference.shape[1], device=reference.device).index_add_(0, assignment[train], reference)
        count = torch.bincount(assignment[train], minlength=k)[:, None]
        mean = sums/count.clamp_min(1)
        result[k] = ((mean*(1-mean)).mean(1)/(mean-reference.mean(0)).var(1).clamp_min(1e-4)).clamp(3, 300)
    return result


def historical_prior(reference, ids, y, target, train_models, model, families, costs, metadata=True):
    observed = reference[ids]
    logit = -(observed-y).square().mean(0)/.02
    if metadata:
        logit += .5*((families[train_models] == families[model]).float()-(costs[train_models].clamp_min(.1).log()-costs[model].clamp_min(.1).log()).abs())
    weight = logit.softmax(0)
    offset = y.mean()-(observed @ weight).mean()
    return (reference[target] @ weight+offset)[:, None], (observed @ weight+offset)[:, None]


@torch.no_grad()
def run(capture, output):
    started = time.monotonic()
    torch.set_num_threads(4)
    output.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((capture / 'manifest.json').read_text())
    for path, digest in manifest['input_sha256'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
    a = {k: torch.tensor(v, device='cpu') for k, v in np.load(capture / 'protocol.npz').items()}
    x = F.normalize(torch.tensor(np.load(f"/data/embedllm_emb_{manifest['encoder']}.npy"), device='cpu').float(), dim=1)
    scores = torch.tensor(np.load('/data/embedllm_scores.npy'), device='cpu').float()
    train, val, test = a['train_q'], a['val_q'], a['test_q']
    train_models, test_models = a['train_models'], a['test_models']
    assert torch.equal(scores[test][:, test_models], a['true_test'])
    labels = {20: a['cluster20'], 100: a['cluster100']}
    parents = torch.tensor([torch.bincount(labels[20][labels[100] == c], minlength=20).argmax() for c in range(100)], device='cpu')
    reference = torch.zeros(len(x), len(train_models), device='cpu')
    reference[train] = scores[train][:, train_models]
    for ids in torch.cat([val, test]).split(1024):
        nearest = (x[ids] @ x[train].T).topk(30, dim=1).indices
        reference[ids] = scores[train][:, train_models][nearest].mean(1)
    eb = historical_strength(labels, train, scores[train][:, train_models])
    fixed = {k: torch.tensor(24., device='cpu') for k in labels}
    shared = dict(strength={k: empirical_strength(labels[k][train], scores[train][:, train_models], k, scores[train][:, train_models].mean(0)) for k in labels})
    target_features = dict(reference=reference[test], labels={k: v[test] for k, v in labels.items()})
    tuning = {}
    for budget in (60, 200, 500, len(val)):
        totals = np.zeros(len(ALPHAS))
        draws = range(5) if budget != len(val) else range(1)
        for seed in draws:
            gen = torch.Generator(device='cpu').manual_seed(777+seed)
            obs = val[torch.randint(len(val), (len(a['val_models']), budget), device='cpu', generator=gen)] if budget != len(val) else val[None].expand(len(a['val_models']), -1)
            candidates = [[] for _ in ALPHAS]
            for model, ids in zip(a['val_models'], obs):
                solver = RidgeSolver(x[ids], x[train[:3000]], scores[ids, model][:, None])
                for row, alpha in zip(candidates, ALPHAS):
                    row.append(solver.predict(alpha).clamp(0, 1))
            for index, values in enumerate(candidates):
                totals[index] += legacy_area(torch.cat(values, 1), scores[train[:3000]][:, a['val_models']], a['costs'][a['val_models']])/len(draws)
        tuning[str(budget)] = dict(alpha=ALPHAS[int(totals.argmax())], validation_areas=totals.tolist())
    (output / 'tuning.json').write_text(json.dumps(tuning, indent=2)+'\n')
    records = []
    for budget in (60, 200, 500, len(val)):
        name = f'k={budget}' if budget != len(val) else f'full-val({budget})'
        for seed in (range(5) if budget != len(val) else range(1)):
            ids = torch.tensor(np.load(capture / f'{seed}_observations_{name}.npy'), device='cpu')
            assert torch.isin(ids, val).all() and not torch.isin(ids, test).any()
            methods = {key: [] for key in ('hier24_parent', 'hier24_query', 'hier_eb', 'hier_prior', 'semantic_ridge', 'flat_mixture')}
            for position, model in enumerate(test_models):
                obs = ids[position]
                y = scores[obs, model][:, None]
                methods['hier24_parent'].append(hierarchy(labels, obs, y, test, fixed, parents))
                methods['hier24_query'].append(hierarchy(labels, obs, y, test, fixed, parents, True))
                methods['hier_eb'].append(hierarchy(labels, obs, y, test, eb, parents))
                prior, fitted = historical_prior(reference, obs, y, test, train_models, model, a['families'], a['costs'])
                residual = y-fitted
                scale = (3*(1-residual.square().mean(0)/(y-y.mean(0)).square().mean(0).clamp_min(1e-3)).clamp(-1, 1)).exp()
                methods['hier_prior'].append(prior+hierarchy(labels, obs, residual, test, {k: v*scale for k, v in eb.items()}, parents))
                solver = RidgeSolver(x[obs], x[test], y)
                methods['semantic_ridge'].append(solver.predict(tuning[str(budget)]['alpha']).clamp(0, 1))
                observed_features = dict(reference=reference[obs], labels={k: v[obs] for k, v in labels.items()})
                state = fit_router('flat_split_uniform', x[obs], y, observed_features, None, shared)
                methods['flat_mixture'].append(predict_router(state, x[test], target_features))
            predictions = {key: torch.cat(value, 1) for key, value in methods.items()}
            for key in ('ICR', 'table', 'uniroute20', 'hier-shrink'):
                predictions[key] = torch.tensor(np.load(capture / f'{seed}_{key} {name}.npy'), device='cpu')
            for key, prediction in predictions.items():
                assert prediction.shape == a['true_test'].shape and torch.isfinite(prediction).all()
                np.save(output / f'{seed}_{key}_{budget}.npy', prediction.cpu().numpy())
                area = legacy_area(prediction, a['true_test'], a['costs'][test_models])
                records.append(dict(method=key, budget=budget, seed=seed, area=area))
            print(json.dumps([r for r in records if r['budget'] == budget and r['seed'] == seed]), flush=True)
    result = dict(encoder=manifest['encoder'], records=records, tuning=tuning, seconds=time.monotonic()-started,
        capture_manifest=manifest, protocol_sha256=hashlib.sha256((capture / 'protocol.npz').read_bytes()).hexdigest())
    (output / 'report.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('capture', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    run(args.capture, args.output)
