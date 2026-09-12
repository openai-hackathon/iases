import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'resources': ['x', 'y'], 'commands': []}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [], 'epochs': {'x': 0, 'y': 0}, 'leases': {}, 'outputs': {'x': [0, None], 'y': [0, None]}}
    assert request == before

def test_one_grant():
    request = {'resources': ['x', 'y'], 'commands': [{'op': 'acquire', 'resources': ['x'], 'owner': 'a', 'now': 0, 'ttl': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'x': 1}], 'epochs': {'x': 1, 'y': 0}, 'leases': {'x': ['a', 1, 10]}, 'outputs': {'x': [0, None], 'y': [0, None]}}
    assert request == before

def test_mixed_busy_grant_rolls_back():
    request = {'resources': ['x', 'y'], 'commands': [{'op': 'acquire', 'resources': ['x'], 'owner': 'a', 'now': 0, 'ttl': 10}, {'op': 'acquire', 'resources': ['x', 'y'], 'owner': 'b', 'now': 1, 'ttl': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'x': 1}, None], 'epochs': {'x': 1, 'y': 0}, 'leases': {'x': ['a', 1, 10]}, 'outputs': {'x': [0, None], 'y': [0, None]}}
    assert request == before

def test_release_reopen_reacquire():
    request = {'resources': ['x', 'y'], 'commands': [{'op': 'acquire', 'resources': ['x'], 'owner': 'a', 'now': 0, 'ttl': 10}, {'op': 'release', 'tokens': {'x': 1}, 'owner': 'a', 'now': 1}, {'op': 'restart'}, {'op': 'acquire', 'resources': ['x'], 'owner': 'a', 'now': 2, 'ttl': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'x': 1}, True, 'restarted', {'x': 2}], 'epochs': {'x': 2, 'y': 0}, 'leases': {'x': ['a', 2, 12]}, 'outputs': {'x': [0, None], 'y': [0, None]}}
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
