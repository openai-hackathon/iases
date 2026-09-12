import copy
import pytest
from fabops.domain import run


def test_initial():
    request = {'route': ['a', 'b'], 'max_retries': 1, 'events': []}
    before = copy.deepcopy(request)
    assert run(request) == {'state': 'active', 'step': 'a', 'retries': 0}
    assert request == before

def test_done():
    request = {'route': ['a'], 'max_retries': 1, 'events': [True]}
    before = copy.deepcopy(request)
    assert run(request) == {'state': 'done', 'step': None, 'retries': 0}
    assert request == before

def test_reset():
    request = {'route': ['a', 'b'], 'max_retries': 1, 'events': [False, True, False]}
    before = copy.deepcopy(request)
    assert run(request) == {'state': 'active', 'step': 'b', 'retries': 1}
    assert request == before

def test_scrap():
    request = {'route': ['a'], 'max_retries': 1, 'events': [False, False]}
    before = copy.deepcopy(request)
    assert run(request) == {'state': 'scrap', 'step': None, 'retries': 2}
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
