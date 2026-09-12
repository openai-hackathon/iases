import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'capacity': 3, 'operations': []}
    before = copy.deepcopy(request)
    assert run(request) == {'admitted': [], 'active': [], 'pending': []}
    assert request == before

def test_one():
    request = {'capacity': 3, 'operations': [{'op': 'enqueue', 'id': 'a', 'weight': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == {'admitted': ['a'], 'active': ['a'], 'pending': []}
    assert request == before

def test_cancel():
    request = {'capacity': 3, 'operations': [{'op': 'enqueue', 'id': 'a', 'weight': 3}, {'op': 'enqueue', 'id': 'b', 'weight': 2}, {'op': 'cancel', 'id': 'b'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'admitted': ['a'], 'active': ['a'], 'pending': []}
    assert request == before

def test_release():
    request = {'capacity': 3, 'operations': [{'op': 'enqueue', 'id': 'a', 'weight': 3}, {'op': 'release', 'id': 'a'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'admitted': ['a'], 'active': [], 'pending': []}
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
