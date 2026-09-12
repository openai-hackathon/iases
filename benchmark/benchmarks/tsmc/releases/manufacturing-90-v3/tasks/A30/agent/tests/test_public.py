import copy
import pytest
from fabops.domain import run


def test_correlated_training():
    request = {'cycles': [{'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': 0.5, 'score': 5.333333, 'decision': 'alarm'}
    assert request == before

def test_exclude_entire_campaign():
    request = {'cycles': [{'id': 'sibling', 'run': 'target-run', 'start': 0, 'end': 2, 'features': [100, 100], 'profile': [100, 100, 0, 130, 0]}, {'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': 0.5, 'score': 5.333333, 'decision': 'alarm'}
    assert request == before

def test_purge_by_end_not_start():
    request = {'cycles': [{'id': 'overlap', 'run': 'overlap', 'start': 8, 'end': 9.5, 'features': [100, 100], 'profile': [100, 100, 0, 130, 0]}, {'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': 0.5, 'score': 5.333333, 'decision': 'alarm'}
    assert request == before

def test_cross_term_sign():
    request = {'cycles': [{'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 3], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 6}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': 0.5, 'score': 5.333333, 'decision': 'normal'}
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
