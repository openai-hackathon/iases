import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def check_prediction(raw, y, c, curve, row):
    maximum = 0.
    c = np.asarray(c, dtype=np.float64)
    p = np.clip(raw.astype(np.float64), 0, 1)
    assert p.shape == y.shape and np.isfinite(p).all()
    x, q = np.array(curve['cost']), np.array(curve['accuracy'])
    assert np.all(np.diff(x) >= -1e-12)
    width = c.max()-c.min()
    area = np.sum(np.diff(x)*(q[:-1]+q[1:])/2)/width
    cap = max(c.min(), .5*c.max())
    xx = np.r_[x[x<cap], cap]
    qq = np.interp(xx, x, q)
    area50 = np.sum(np.diff(xx)*(qq[:-1]+qq[1:])/2)/width
    np.testing.assert_allclose([area, area50], [row['area'], row['area50']], rtol=0, atol=1e-10)
    target = row['best_single_accuracy']
    crossing = None
    for i in range(len(q)):
        if q[i] >= target-1e-7:
            crossing = x[i]
            if i and q[i-1] < target and q[i] >= target and q[i] > q[i-1]:
                crossing = x[i-1]+(target-q[i-1])*(x[i]-x[i-1])/(q[i]-q[i-1])
            break
    assert (crossing is not None) == row['reached_best']
    if crossing is not None:
        np.testing.assert_allclose(crossing/row['best_single_cost'], row['qnc'], atol=1e-7)
    ordering = np.argsort(c, kind='stable')
    for weight in np.geomspace(.0000137, 137, 17)/c.max():
        chosen = ordering[(p[:,ordering]-weight*c[ordering]).argmax(1)]
        cost = c[chosen].mean()
        quality = y[np.arange(len(y)),chosen].mean()
        error = abs(quality-np.interp(cost, x, q))
        maximum = max(maximum, error)
        assert error < 1e-7, error
    return maximum


def verify(directory):
    report = json.loads((directory/'report.json').read_text())
    curves = json.loads((directory/'curves.json').read_text())
    protocol = dict(np.load(directory/'protocol.npz'))
    groups = [protocol[key] for key in ('train','val','test')]
    assert all(len(np.unique(g)) == len(g) for g in groups)
    assert len(np.unique(np.concatenate(groups))) == sum(map(len, groups))
    assert not np.intersect1d(protocol['train_models'], protocol['test_models']).size
    np.testing.assert_array_equal(np.sort(protocol['observed']), np.sort(protocol['val']))
    loaded = {}
    maximum = 0.
    checked = 0
    for row in report['records']:
        budget, name = row['budget'], row['method']
        if budget not in loaded:
            path = directory/('static_predictions.npz' if budget == 'static' else f'predictions_{budget}.npz')
            loaded = {budget: dict(np.load(path))}
        raw = loaded[budget][name]
        y = protocol['static_quality' if budget == 'static' else 'quality'].astype(np.float64)
        models = protocol['train_models' if budget == 'static' else 'test_models']
        c = protocol['costs'][models]
        maximum = max(maximum, check_prediction(raw, y, c, curves[f'{budget}/{name}'], row))
        checked += 1
    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(directory.iterdir())
        if path.suffix in ('.json','.npz','.npy','.pt') and path.name != 'verification.json'}
    result = dict(files_sha256=hashes, checked=checked, direct_policy_points=17*checked, max_policy_quality_error=maximum,
        split_disjoint=True, observation_is_validation_permutation=True,
        report_sha256=hashlib.sha256((directory/'report.json').read_bytes()).hexdigest())
    (directory/'verification.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    verify(args.directory)
