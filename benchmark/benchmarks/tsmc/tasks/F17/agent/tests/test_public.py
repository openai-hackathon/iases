import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'stock': {}, 'orders': []}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [], 'stock': {}}
    assert request == before

def test_one():
    request = {'stock': {'a': 3}, 'orders': [{'a': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True], 'stock': {'a': 2}}
    assert request == before

def test_reject():
    request = {'stock': {'a': 1, 'b': 0}, 'orders': [{'a': 1, 'b': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [False], 'stock': {'a': 1, 'b': 0}}
    assert request == before

def test_exact():
    request = {'stock': {'a': 1}, 'orders': [{'a': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True], 'stock': {'a': 0}}
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
