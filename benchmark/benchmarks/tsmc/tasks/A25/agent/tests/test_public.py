import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'seeds': [], 'edges': []}
    before = copy.deepcopy(request)
    assert run(request) == []
    assert request == before

def test_direct():
    request = {'seeds': ['a'], 'edges': [['a', 'b']]}
    before = copy.deepcopy(request)
    assert run(request) == ['b']
    assert request == before

def test_chain():
    request = {'seeds': ['a'], 'edges': [['a', 'b'], ['b', 'c']]}
    before = copy.deepcopy(request)
    assert run(request) == ['b', 'c']
    assert request == before

def test_unknown():
    request = {'seeds': ['z'], 'edges': [['a', 'b']]}
    before = copy.deepcopy(request)
    assert run(request) == []
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
