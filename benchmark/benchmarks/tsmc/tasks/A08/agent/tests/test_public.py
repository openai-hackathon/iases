import copy
import pytest
from fabops.domain import run


def test_interior():
    request = {'edges': [0, 10, 20], 'values': [5, 15]}
    before = copy.deepcopy(request)
    assert run(request) == [1, 1]
    assert request == before

def test_last_edge():
    request = {'edges': [0, 10, 20], 'values': [20]}
    before = copy.deepcopy(request)
    assert run(request) == [0, 1]
    assert request == before

def test_outside():
    request = {'edges': [0, 10], 'values': [-1, 11]}
    before = copy.deepcopy(request)
    assert run(request) == [0]
    assert request == before

def test_empty():
    request = {'edges': [0, 10], 'values': []}
    before = copy.deepcopy(request)
    assert run(request) == [0]
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
