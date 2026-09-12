import copy
import pytest
from fabops.domain import run


def test_linear_control():
    request = {'capacities': {'done': 3, 'raw': 3}, 'initial': {'raw': 1}, 'final': {'done': 1}, 'transitions': [{'id': 'etch', 'label': 'etch', 'consume': {'raw': 1}, 'produce': {'done': 1}}], 'trace': ['etch']}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'witness': ['etch'], 'silent': 0, 'marking': {'done': 1, 'raw': 0}}
    assert request == before

def test_parallel_join():
    request = {'capacities': {'a': 3, 'a_done': 3, 'b': 3, 'b_done': 3, 'done': 3, 'raw': 3}, 'initial': {'raw': 1}, 'final': {'done': 1}, 'transitions': [{'id': 'split', 'label': None, 'consume': {'raw': 1}, 'produce': {'a': 1, 'b': 1}}, {'id': 'measure', 'label': 'measure', 'consume': {'a': 1}, 'produce': {'a_done': 1}}, {'id': 'clean', 'label': 'clean', 'consume': {'b': 1}, 'produce': {'b_done': 1}}, {'id': 'join', 'label': None, 'consume': {'a_done': 1, 'b_done': 1}, 'produce': {'done': 1}}], 'trace': ['clean', 'measure']}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'witness': ['split', 'clean', 'measure', 'join'], 'silent': 2, 'marking': {'a': 0, 'a_done': 0, 'b': 0, 'b_done': 0, 'done': 1, 'raw': 0}}
    assert request == before

def test_weighted_self_loop_unavailable():
    request = {'capacities': {'p': 3}, 'initial': {'p': 1}, 'final': {'p': 1}, 'transitions': [{'id': 'batch', 'label': 'inspect', 'consume': {'p': 2}, 'produce': {'p': 2}}], 'trace': ['inspect']}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': False, 'witness': [], 'silent': None, 'marking': {'p': 1}}
    assert request == before

def test_leftover_parallel_token():
    request = {'capacities': {'done': 3, 'hold': 3, 'raw': 3}, 'initial': {'raw': 1, 'hold': 1}, 'final': {'done': 1}, 'transitions': [{'id': 'etch', 'label': 'etch', 'consume': {'raw': 1}, 'produce': {'done': 1}}], 'trace': ['etch']}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': False, 'witness': [], 'silent': None, 'marking': {'done': 0, 'hold': 1, 'raw': 1}}
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
