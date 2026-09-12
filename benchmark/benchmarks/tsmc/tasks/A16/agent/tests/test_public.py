import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'baseline': [0, 2], 'k': 1, 'measurements': []}
    before = copy.deepcopy(request)
    assert run(request) == []
    assert request == before

def test_center():
    request = {'baseline': [0, 2], 'k': 1, 'measurements': [1]}
    before = copy.deepcopy(request)
    assert run(request) == [False]
    assert request == before

def test_spike():
    request = {'baseline': [0, 2], 'k': 2, 'measurements': [100]}
    before = copy.deepcopy(request)
    assert run(request) == [True]
    assert request == before

def test_flat():
    request = {'baseline': [1, 1], 'k': 2, 'measurements': [1]}
    before = copy.deepcopy(request)
    assert run(request) == [False]
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
