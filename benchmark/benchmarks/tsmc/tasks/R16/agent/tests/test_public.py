import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'threshold': 2, 'cooldown': 5, 'events': []}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [], 'state': 'closed', 'failures': 0}
    assert request == before

def test_success():
    request = {'threshold': 2, 'cooldown': 5, 'events': [{'now': 0, 'success': True}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True], 'state': 'closed', 'failures': 0}
    assert request == before

def test_reset():
    request = {'threshold': 2, 'cooldown': 5, 'events': [{'now': 0, 'success': False}, {'now': 1, 'success': True}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True, True], 'state': 'closed', 'failures': 0}
    assert request == before

def test_opens():
    request = {'threshold': 2, 'cooldown': 5, 'events': [{'now': 0, 'success': False}, {'now': 1, 'success': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True, True], 'state': 'open', 'failures': 2}
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
