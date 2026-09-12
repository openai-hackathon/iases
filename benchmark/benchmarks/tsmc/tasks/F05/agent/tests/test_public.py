import copy
import pytest
from fabops.domain import run


def test_fresh():
    request = {'now': 10, 'lots': [{'expires_at': 11}]}
    before = copy.deepcopy(request)
    assert run(request) == [True]
    assert request == before

def test_expired():
    request = {'now': 10, 'lots': [{'expires_at': 9}]}
    before = copy.deepcopy(request)
    assert run(request) == [False]
    assert request == before

def test_boundary():
    request = {'now': 10, 'lots': [{'expires_at': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == [False]
    assert request == before

def test_empty():
    request = {'now': 10, 'lots': []}
    before = copy.deepcopy(request)
    assert run(request) == []
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
