import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'summaries': []}
    before = copy.deepcopy(request)
    assert run(request) == {'count': 0, 'mean': None, 'variance': None}
    assert request == before

def test_single():
    request = {'summaries': [{'count': 2, 'mean': 2, 'm2': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == {'count': 2, 'mean': 2.0, 'variance': 1.0}
    assert request == before

def test_different_means():
    request = {'summaries': [{'count': 1, 'mean': 0, 'm2': 0}, {'count': 1, 'mean': 4, 'm2': 0}]}
    before = copy.deepcopy(request)
    assert run(request) == {'count': 2, 'mean': 2.0, 'variance': 4.0}
    assert request == before

def test_equal_means():
    request = {'summaries': [{'count': 2, 'mean': 2, 'm2': 2}, {'count': 2, 'mean': 2, 'm2': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == {'count': 4, 'mean': 2.0, 'variance': 1.0}
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
