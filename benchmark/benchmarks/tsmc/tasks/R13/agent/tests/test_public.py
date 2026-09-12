import copy
import pytest
from fabops.domain import run


def test_single():
    request = {'commands': [{'op': 'join', 'waiter': 'a', 'job': 'p', 'scope': 'cell', 'key': 'sensor', 'resistant': False}, {'op': 'finish', 'job': 'p', 'value': 3}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': {'a': {'status': 'value', 'value': 3}}, 'calls': [['p', 'cell', 'sensor', 0]], 'cancellations': [], 'active': 0}
    assert request == before

def test_scopes_do_not_share():
    request = {'commands': [{'op': 'join', 'waiter': 'a', 'job': 'p', 'scope': 'x', 'key': 'sensor', 'resistant': False}, {'op': 'join', 'waiter': 'b', 'job': 'q', 'scope': 'y', 'key': 'sensor', 'resistant': False}, {'op': 'finish', 'job': 'p', 'value': 1}, {'op': 'finish', 'job': 'q', 'value': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': {'a': {'status': 'value', 'value': 1}, 'b': {'status': 'value', 'value': 2}}, 'calls': [['p', 'x', 'sensor', 0], ['q', 'y', 'sensor', 0]], 'cancellations': [], 'active': 0}
    assert request == before

def test_cancel_one_follower():
    request = {'commands': [{'op': 'join', 'waiter': 'a', 'job': 'p', 'scope': 'cell', 'key': 'sensor', 'resistant': False}, {'op': 'join', 'waiter': 'b', 'job': 'q', 'scope': 'cell', 'key': 'sensor', 'resistant': False}, {'op': 'cancel', 'waiter': 'a'}, {'op': 'finish', 'job': 'p', 'value': 4}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': {'a': {'status': 'cancelled'}, 'b': {'status': 'value', 'value': 4}}, 'calls': [['p', 'cell', 'sensor', 0]], 'cancellations': [], 'active': 0}
    assert request == before

def test_new_generation_runs_independently():
    request = {'commands': [{'op': 'join', 'waiter': 'a', 'job': 'p', 'scope': 'cell', 'key': 'sensor', 'resistant': False}, {'op': 'invalidate', 'scope': 'cell'}, {'op': 'join', 'waiter': 'b', 'job': 'q', 'scope': 'cell', 'key': 'sensor', 'resistant': False}, {'op': 'finish', 'job': 'q', 'value': 2}, {'op': 'finish', 'job': 'p', 'value': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': {'a': {'status': 'value', 'value': 1}, 'b': {'status': 'value', 'value': 2}}, 'calls': [['p', 'cell', 'sensor', 0], ['q', 'cell', 'sensor', 1]], 'cancellations': [], 'active': 0}
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
