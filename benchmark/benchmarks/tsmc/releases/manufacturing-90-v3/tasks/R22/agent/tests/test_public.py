import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'commands': []}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [], 'value': None, 'epoch': 0}
    assert request == before

def test_first():
    request = {'commands': [{'op': 'acquire', 'owner': 'a', 'now': 0, 'ttl': 10}, {'op': 'write', 'owner': 'a', 'token': 1, 'now': 1, 'value': 'ok'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, True], 'value': 'ok', 'epoch': 1}
    assert request == before

def test_retire_reacquire():
    request = {'commands': [{'op': 'acquire', 'owner': 'a', 'now': 0, 'ttl': 10}, {'op': 'retire'}, {'op': 'acquire', 'owner': 'a', 'now': 2, 'ttl': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, None, 2], 'value': None, 'epoch': 2}
    assert request == before

def test_busy():
    request = {'commands': [{'op': 'acquire', 'owner': 'a', 'now': 0, 'ttl': 10}, {'op': 'acquire', 'owner': 'b', 'now': 2, 'ttl': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, None], 'value': None, 'epoch': 1}
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
