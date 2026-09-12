import copy
import pytest
from fabops.domain import run


def test_correlated_training():
    request = {'cycles': [{'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': [[1.0, 0.5], [0.5, 1.0]], 'score': 5.333333, 'decision': 'alarm', 'calibration': [], 'threshold': 5}
    assert request == before

def test_exclude_entire_campaign():
    request = {'cycles': [{'id': 'sibling', 'run': 'target-run', 'start': 0, 'end': 2, 'features': [100, 100], 'profile': [100, 100, 0, 130, 0]}, {'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': [[1.0, 0.5], [0.5, 1.0]], 'score': 5.333333, 'decision': 'alarm', 'calibration': [], 'threshold': 5}
    assert request == before

def test_purge_by_end_not_start():
    request = {'cycles': [{'id': 'overlap', 'run': 'overlap', 'start': 8, 'end': 9.5, 'features': [100, 100], 'profile': [100, 100, 0, 130, 0]}, {'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': [[1.0, 0.5], [0.5, 1.0]], 'score': 5.333333, 'decision': 'alarm', 'calibration': [], 'threshold': 5}
    assert request == before

def test_cross_term_sign():
    request = {'cycles': [{'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 3], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 6}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': [[1.0, 0.5], [0.5, 1.0]], 'score': 5.333333, 'decision': 'normal', 'calibration': [], 'threshold': 6}
    assert request == before

def test_unequal_campaign_mass():
    request = {'cycles': [{'end': 1, 'features': [0, 0], 'id': 'a', 'profile': [100, 100, 0, 130, 0], 'run': 'old', 'start': 0}, {'end': 3, 'features': [2, 2], 'id': 'b', 'profile': [100, 100, 0, 130, 0], 'run': 'old', 'start': 2}, {'end': 5, 'features': [4, 0], 'id': 'c', 'profile': [100, 100, 0, 130, 0], 'run': 'new', 'start': 4}, {'end': 21, 'features': [3, 1], 'id': 't', 'profile': [100, 100, 0, 130, 0], 'run': 'target', 'start': 20}], 'embargo': 0, 'min_train': 2, 'shrinkage': 0.5, 'target': 't', 'threshold': 3}
    before = copy.deepcopy(request)
    assert run(request) == {'calibration': [], 'center': [2.5, 0.5], 'correlation': [[1.0, -0.087039], [-0.087039, 1.0]], 'decision': 'normal', 'scale': [1.658312, 0.866025], 'score': 0.458015, 'threshold': 3, 'training': ['a', 'b', 'c']}
    assert request == before

def test_observed_principal_subspace():
    request = {'cycles': [{'end': 1, 'features': [0, 0], 'id': 'a', 'profile': [100, 100, 0, 130, 0], 'run': 'old', 'start': 0}, {'end': 3, 'features': [2, 2], 'id': 'b', 'profile': [100, 100, 0, 130, 0], 'run': 'old', 'start': 2}, {'end': 5, 'features': [4, 0], 'id': 'c', 'profile': [100, 100, 0, 130, 0], 'run': 'new', 'start': 4}, {'end': 21, 'features': [3, None], 'id': 't', 'profile': [100, 100, 0, 130, 0], 'run': 'target', 'start': 20}], 'embargo': 0, 'min_observed': 1, 'min_train': 2, 'shrinkage': 0.5, 'target': 't', 'threshold': 3}
    before = copy.deepcopy(request)
    assert run(request) == {'calibration': [], 'center': [2.5, 0.5], 'correlation': [[1.0, -0.087039], [-0.087039, 1.0]], 'decision': 'normal', 'scale': [1.658312, 0.866025], 'score': 0.181818, 'threshold': 3, 'training': ['a', 'b', 'c']}
    assert request == before

def test_purged_run_calibration():
    request = {'alpha': 0.5, 'calibrate': True, 'cycles': [{'end': 1, 'features': [0, 0], 'id': 'a', 'profile': [100, 100, 0, 130, 0], 'run': 'old', 'start': 0}, {'end': 3, 'features': [2, 2], 'id': 'b', 'profile': [100, 100, 0, 130, 0], 'run': 'old', 'start': 2}, {'end': 5, 'features': [4, 0], 'id': 'c', 'profile': [100, 100, 0, 130, 0], 'run': 'new', 'start': 4}, {'end': 21, 'features': [3, 1], 'id': 't', 'profile': [100, 100, 0, 130, 0], 'run': 'target', 'start': 20}], 'embargo': 0, 'min_train': 2, 'shrinkage': 0.5, 'target': 't', 'threshold': 3}
    before = copy.deepcopy(request)
    assert run(request) == {'calibration': [['new', 17.333333]], 'center': [2.5, 0.5], 'correlation': [[1.0, -0.087039], [-0.087039, 1.0]], 'decision': 'normal', 'scale': [1.658312, 0.866025], 'score': 0.458015, 'threshold': 17.333333, 'training': ['a', 'b', 'c']}
    assert request == before


def test_public_cli_fixture():
    import json
    from pathlib import Path
    import subprocess
    import sys
    completed = subprocess.run(
        [sys.executable, "-m", "fabops", "--input", "data/request.json"],
        capture_output=True, text=True, timeout=10, check=True)
    assert json.loads(completed.stdout) == json.loads(Path("data/expected.json").read_text())
