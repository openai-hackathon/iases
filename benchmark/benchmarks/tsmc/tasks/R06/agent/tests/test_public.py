import copy
import pytest
from fabops.domain import run


def test_initial():
    request = {'base': 1, 'cap': 10, 'attempt': 0, 'jitter': 0}
    before = copy.deepcopy(request)
    assert run(request) == 1
    assert request == before

def test_second():
    request = {'base': 1, 'cap': 10, 'attempt': 1, 'jitter': 1}
    before = copy.deepcopy(request)
    assert run(request) == 3
    assert request == before

def test_capped():
    request = {'base': 1, 'cap': 10, 'attempt': 4, 'jitter': 2}
    before = copy.deepcopy(request)
    assert run(request) == 10
    assert request == before

def test_exact_cap():
    request = {'base': 1, 'cap': 8, 'attempt': 3, 'jitter': 0}
    before = copy.deepcopy(request)
    assert run(request) == 8
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
