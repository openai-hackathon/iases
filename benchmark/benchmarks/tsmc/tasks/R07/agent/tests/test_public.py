import copy
import pytest
from fabops.domain import run


def test_fresh():
    request = {'created': 10, 'ttl': 5, 'now': 12, 'value': 'ok'}
    before = copy.deepcopy(request)
    assert run(request) == 'ok'
    assert request == before

def test_old():
    request = {'created': 10, 'ttl': 5, 'now': 16, 'value': 'ok'}
    before = copy.deepcopy(request)
    assert run(request) == None
    assert request == before

def test_boundary():
    request = {'created': 10, 'ttl': 5, 'now': 15, 'value': 'ok'}
    before = copy.deepcopy(request)
    assert run(request) == None
    assert request == before

def test_empty_value():
    request = {'created': 0, 'ttl': 10, 'now': 1, 'value': ''}
    before = copy.deepcopy(request)
    assert run(request) == ''
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
