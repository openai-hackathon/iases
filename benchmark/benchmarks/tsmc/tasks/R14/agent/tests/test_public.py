import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'lease': {'owner': 'a', 'expires': 10}, 'renewals': []}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [], 'lease': {'owner': 'a', 'expires': 10}}
    assert request == before

def test_owner():
    request = {'lease': {'owner': 'a', 'expires': 10}, 'renewals': [{'owner': 'a', 'now': 5, 'ttl': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True], 'lease': {'owner': 'a', 'expires': 15}}
    assert request == before

def test_other():
    request = {'lease': {'owner': 'a', 'expires': 10}, 'renewals': [{'owner': 'b', 'now': 5, 'ttl': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [False], 'lease': {'owner': 'a', 'expires': 10}}
    assert request == before

def test_expired():
    request = {'lease': {'owner': 'a', 'expires': 10}, 'renewals': [{'owner': 'a', 'now': 11, 'ttl': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [False], 'lease': {'owner': 'a', 'expires': 10}}
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
