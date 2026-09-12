import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np
import torch

from final_estimators_cpu import ROOT
from research40.mapped_selector import MappedSelector
from uniroute_aligned import map_network


def compile_map(network):
    state = {key: value.detach().cpu().numpy().astype(np.float64) for key, value in network.state_dict().items()}
    arrays = {}
    for i, linear, normalizer in ((0, 1, 2), (1, 4, 5)):
        scale = state[f'{normalizer}.weight'] / np.sqrt(state[f'{normalizer}.running_var'] + network[normalizer].eps)
        shift = state[f'{normalizer}.bias'] - scale * state[f'{normalizer}.running_mean']
        weight = scale[:, None] * state[f'{linear}.weight']
        bias = scale * state[f'{linear}.bias'] + shift
        if i == 0:
            before_scale = state['0.weight'] / np.sqrt(state['0.running_var'] + network[0].eps)
            before_shift = state['0.bias'] - before_scale * state['0.running_mean']
            bias += weight @ before_shift
            weight = weight * before_scale[None]
        arrays[f'w{i}'], arrays[f'b{i}'] = weight, bias
    arrays['w2'], arrays['b2'] = state['7.weight'], state['7.bias']
    return arrays


def measure(selector, queries, expected, counts, kind, dataset):
    records = []
    for count in counts:
        candidates = selector.models[:count]
        for query in queries[:16]:
            selector.select(query, .1, candidates)
        for i, query in enumerate(queries):
            weight = (0., .03, .1, .3)[i % 4]
            started = time.perf_counter_ns()
            result = selector.select(query, weight, candidates)
            elapsed = (time.perf_counter_ns()-started) / 1e6
            utility = expected[i, :count] - weight*selector.costs[:count]
            target = int(utility.argmax())
            selected = selector.models.index(result['model'])
            sorted_utility = np.sort(utility)
            gap = None if count == 1 else float(sorted_utility[-1]-sorted_utility[-2])
            records.append(dict(dataset=dataset, kind=kind, eligible=count, query=i, weight=weight, ms=elapsed, disagreement=selected != target, reference_gap=gap, **result))
    return records


@torch.no_grad()
def main():
    started = time.monotonic()
    torch.set_num_threads(4)
    output = ROOT / 'results/mapped_selector_cpu'
    output.mkdir(parents=True, exist_ok=True)
    assert not (output / 'report.json').exists()
    records, checks, paths = [], [], [Path(__file__), ROOT / 'experiments/research40/mapped_selector.py', ROOT / 'experiments/uniroute_aligned.py']
    for dataset in ('embedllm', 'routerbench'):
        source = ROOT / 'results/uniroute_text_cpu' / dataset / '20260920'
        followup = ROOT / 'results/frozen_reference_cpu' / dataset / '20260920'
        protocol = dict(np.load(source / 'protocol.npz'))
        raw_path = ROOT / 'data' / ('embedllm_emb_bge.npy' if dataset == 'embedllm' else 'emb_0shot.npy')
        queries = np.load(raw_path, mmap_mode='r')[protocol['test'][:256]]
        profile = np.load(followup / 'reference/signals.npz')['profile']
        network = map_network(queries.shape[1], len(profile))
        network.load_state_dict(torch.load(source / 'learnedmap.pt', weights_only=True, map_location='cpu'))
        network.eval()
        state = torch.load(followup / 'routing/200_mapped_hier_state.pt', weights_only=True, map_location='cpu')
        costs = protocol['costs'][protocol['test_models']]
        artifact = dict(compile_map(network), profile=profile.astype(np.float64) @ state['weights'].numpy().astype(np.float64), offset=state['offset'].numpy().reshape(-1).astype(np.float64), table=state['table'].numpy().astype(np.float64), centers=np.load(source / 'hierarchy_centers_100.npy').astype(np.float64), models=np.array([f'column_{value}' for value in protocol['test_models']]), costs=costs/costs.max())
        path = output / f'{dataset}_profile.npz'
        np.savez(path, **artifact)
        selector = MappedSelector(path)
        expected = np.load(followup / 'routing/200_mapped_hier.npz')['prediction'][:len(queries)].clip(0, 1)
        actual = np.stack([selector.scores(query) for query in queries])
        error = float(np.max(np.abs(actual-expected)))
        np.testing.assert_allclose(actual, expected, atol=4e-6, rtol=0)
        checks.append(dict(dataset=dataset, queries=len(queries), maximum_score_error=error, artifact_bytes=path.stat().st_size, array_bytes=sum(value.nbytes for value in artifact.values()), test_ids=protocol['test'][:len(queries)].tolist()))
        records.extend(measure(selector, queries, expected, (1, len(selector.models)), 'real_profile', dataset))
        paths += [path, raw_path, source / 'protocol.npz', source / 'learnedmap.pt', source / 'hierarchy_centers_100.npy', followup / 'reference/signals.npz', followup / 'routing/200_mapped_hier_state.pt', followup / 'routing/200_mapped_hier.npz']
        if dataset == 'embedllm':
            synthetic = dict(artifact, profile=np.tile(artifact['profile'][:, :1], (1, 100)), offset=np.linspace(-.1, .1, 100), table=np.tile(artifact['table'][:, :1], (1, 100)), models=np.array([f'synthetic_{i}' for i in range(100)]), costs=np.linspace(0, 1, 100))
            path = output / 'synthetic_profile.npz'
            np.savez(path, **synthetic)
            scale_selector = MappedSelector(path)
            scale_expected = np.stack([scale_selector.scores(query) for query in queries])
            records.extend(measure(scale_selector, queries, scale_expected, (1, 10, 100), 'synthetic_scale', dataset))
            paths.append(path)
    summary = []
    for dataset, kind, count in sorted({(r['dataset'], r['kind'], r['eligible']) for r in records}):
        rows = [r for r in records if (r['dataset'], r['kind'], r['eligible']) == (dataset, kind, count)]
        times = [r['ms'] for r in rows]
        summary.append(dict(dataset=dataset, kind=kind, eligible=count, queries=len(rows), p50_ms=float(np.median(times)), p99_ms=float(np.quantile(times, .99)), disagreements=sum(r['disagreement'] for r in rows)))
    report = dict(summary=summary, records=records, checks=checks, source_sha256={str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}, nice=os.getpriority(os.PRIO_PROCESS, 0), seconds=time.monotonic()-started, raw_text_encoder_included=False, query_time_training=False, runtime='NumPy float64; OpenBLAS one thread; no Torch in selector', cost_unit='Archived model costs divided by the maximum within the pool')
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    (ROOT / 'results/logs/mapped_selector_summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(summary=summary, checks=checks), indent=2), flush=True)


if __name__ == '__main__':
    main()
