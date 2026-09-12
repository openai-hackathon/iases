import copy
import pytest
from fabops.domain import run


def test_quiet():
    request = {'low': 2, 'high': 5, 'initial': False, 'values': [1, 3, 4]}
    before = copy.deepcopy(request)
    assert run(request) == [False, False, False]
    assert request == before

def test_equality():
    request = {'low': 2, 'high': 5, 'initial': False, 'values': [5]}
    before = copy.deepcopy(request)
    assert run(request) == [True]
    assert request == before

def test_empty():
    request = {'low': 2, 'high': 5, 'initial': False, 'values': []}
    before = copy.deepcopy(request)
    assert run(request) == []
    assert request == before

def test_above():
    request = {'low': 2, 'high': 5, 'initial': False, 'values': [6]}
    before = copy.deepcopy(request)
    assert run(request) == [True]
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
