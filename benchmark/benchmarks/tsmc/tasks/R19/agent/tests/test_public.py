import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'events': []}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [], 'completed': [], 'active': [], 'state': 'open'}
    assert request == before

def test_normal():
    request = {'events': [{'op': 'start', 'id': 'a'}, {'op': 'finish', 'id': 'a'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': ['a'], 'completed': ['a'], 'active': [], 'state': 'open'}
    assert request == before

def test_drain():
    request = {'events': [{'op': 'start', 'id': 'a'}, {'op': 'shutdown'}, {'op': 'finish', 'id': 'a'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': ['a'], 'completed': ['a'], 'active': [], 'state': 'closed'}
    assert request == before

def test_idle_shutdown():
    request = {'events': [{'op': 'shutdown'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [], 'completed': [], 'active': [], 'state': 'closed'}
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
