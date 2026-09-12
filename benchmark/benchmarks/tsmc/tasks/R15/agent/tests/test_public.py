import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'capacity': 4, 'operations': []}
    before = copy.deepcopy(request)
    assert run(request) == {'keys': [], 'weight': 0}
    assert request == before

def test_one():
    request = {'capacity': 4, 'operations': [{'op': 'put', 'key': 'a', 'weight': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == {'keys': ['a'], 'weight': 2}
    assert request == before

def test_oversized():
    request = {'capacity': 4, 'operations': [{'op': 'put', 'key': 'a', 'weight': 2}, {'op': 'put', 'key': 'b', 'weight': 5}]}
    before = copy.deepcopy(request)
    assert run(request) == {'keys': ['a'], 'weight': 2}
    assert request == before

def test_evict():
    request = {'capacity': 4, 'operations': [{'op': 'put', 'key': 'a', 'weight': 3}, {'op': 'put', 'key': 'b', 'weight': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == {'keys': ['b'], 'weight': 2}
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
