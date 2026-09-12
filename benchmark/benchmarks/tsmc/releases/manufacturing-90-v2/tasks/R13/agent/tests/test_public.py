import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'rounds': []}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [], 'calls': {}}
    assert request == before

def test_one():
    request = {'rounds': [{'keys': ['a'], 'cancel': []}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [['a']], 'calls': {'a': 1}}
    assert request == before

def test_cancel_one():
    request = {'rounds': [{'keys': ['a', 'a'], 'cancel': [0]}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [['cancelled', 'a']], 'calls': {'a': 1}}
    assert request == before

def test_shared():
    request = {'rounds': [{'keys': ['a', 'a'], 'cancel': []}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [['a', 'a']], 'calls': {'a': 1}}
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
