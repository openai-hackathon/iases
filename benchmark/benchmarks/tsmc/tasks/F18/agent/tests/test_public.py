import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'stock': {'a': 4}, 'operations': []}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [], 'stock': {'a': 4}}
    assert request == before

def test_split():
    request = {'stock': {'a': 4}, 'operations': [{'inputs': ['a'], 'outputs': {'b': 1, 'c': 3}}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True], 'stock': {'b': 1, 'c': 3}}
    assert request == before

def test_loss():
    request = {'stock': {'a': 4}, 'operations': [{'inputs': ['a'], 'outputs': {'b': 3}}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [False], 'stock': {'a': 4}}
    assert request == before

def test_gain():
    request = {'stock': {'a': 4}, 'operations': [{'inputs': ['a'], 'outputs': {'b': 5}}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [False], 'stock': {'a': 4}}
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
