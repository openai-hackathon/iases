import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'commands': []}
    before = copy.deepcopy(request)
    assert run(request) == []
    assert request == before

def test_one():
    request = {'commands': [{'key': 'k', 'method': 'POST', 'target': '/lot', 'payload': {}, 'result': 'a'}]}
    before = copy.deepcopy(request)
    assert run(request) == ['a']
    assert request == before

def test_key_order():
    request = {'commands': [{'key': 'k', 'method': 'POST', 'target': '/lot', 'payload': {'a': 1, 'b': 2}, 'result': 'a'}, {'key': 'k', 'method': 'POST', 'target': '/lot', 'payload': {'b': 2, 'a': 1}, 'result': 'b'}]}
    before = copy.deepcopy(request)
    assert run(request) == ['a', 'a']
    assert request == before

def test_same():
    request = {'commands': [{'key': 'k', 'method': 'POST', 'target': '/lot', 'payload': {}, 'result': 'a'}, {'key': 'k', 'method': 'POST', 'target': '/lot', 'payload': {}, 'result': 'b'}]}
    before = copy.deepcopy(request)
    assert run(request) == ['a', 'a']
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
