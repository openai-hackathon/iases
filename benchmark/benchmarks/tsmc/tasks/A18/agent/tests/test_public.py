import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'readings': [], 'queries': [1], 'tolerance': 2}
    before = copy.deepcopy(request)
    assert run(request) == [None]
    assert request == before

def test_exact():
    request = {'readings': [[1, 4]], 'queries': [1], 'tolerance': 0}
    before = copy.deepcopy(request)
    assert run(request) == [4]
    assert request == before

def test_stale():
    request = {'readings': [[0, 4]], 'queries': [10], 'tolerance': 2}
    before = copy.deepcopy(request)
    assert run(request) == [None]
    assert request == before

def test_future_far():
    request = {'readings': [[10, 4]], 'queries': [0], 'tolerance': 2}
    before = copy.deepcopy(request)
    assert run(request) == [None]
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
