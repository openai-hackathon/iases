import copy
import pytest
from fabops.domain import run


def test_exact_control():
    request = {'initial': {'raw': 1}, 'final': {'done': 1}, 'capacities': {'done': 3, 'raw': 3}, 'transitions': [{'id': 'work', 'label': 'work', 'consume': {'raw': 1}, 'produce': {'done': 1}, 'model_cost': 2}], 'groups': [[{'id': 'w', 'label': 'work', 'skip_cost': 5}]]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'cost': 0, 'alignment': [{'kind': 'sync', 'event': 'w', 'transition': 'work'}], 'log_moves': 0, 'model_moves': 0, 'synchronous_moves': 1}
    assert request == before

def test_missing_event():
    request = {'initial': {'raw': 1}, 'final': {'done': 1}, 'capacities': {'done': 3, 'raw': 3}, 'transitions': [{'id': 'work', 'label': 'work', 'consume': {'raw': 1}, 'produce': {'done': 1}, 'model_cost': 2}], 'groups': []}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'cost': 2, 'alignment': [{'kind': 'model', 'event': None, 'transition': 'work'}], 'log_moves': 0, 'model_moves': 1, 'synchronous_moves': 0}
    assert request == before

def test_extra_observation():
    request = {'initial': {'raw': 1}, 'final': {'done': 1}, 'capacities': {'done': 3, 'raw': 3}, 'transitions': [{'id': 'work', 'label': 'work', 'consume': {'raw': 1}, 'produce': {'done': 1}, 'model_cost': 2}], 'groups': [[{'id': 'x', 'label': 'noise', 'skip_cost': 3}], [{'id': 'w', 'label': 'work', 'skip_cost': 5}]]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'cost': 3, 'alignment': [{'kind': 'log', 'event': 'x', 'transition': None}, {'kind': 'sync', 'event': 'w', 'transition': 'work'}], 'log_moves': 1, 'model_moves': 0, 'synchronous_moves': 1}
    assert request == before

def test_unordered_group():
    request = {'initial': {'raw': 1}, 'final': {'done': 1}, 'capacities': {'done': 3, 'mid': 3, 'raw': 3}, 'transitions': [{'id': 'first', 'label': 'a', 'consume': {'raw': 1}, 'produce': {'mid': 1}, 'model_cost': 2}, {'id': 'second', 'label': 'b', 'consume': {'mid': 1}, 'produce': {'done': 1}, 'model_cost': 2}], 'groups': [[{'id': 'b', 'label': 'b', 'skip_cost': 5}, {'id': 'a', 'label': 'a', 'skip_cost': 5}]]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'cost': 0, 'alignment': [{'kind': 'sync', 'event': 'a', 'transition': 'first'}, {'kind': 'sync', 'event': 'b', 'transition': 'second'}], 'log_moves': 0, 'model_moves': 0, 'synchronous_moves': 2}
    assert request == before

def test_matching_label_dead_end():
    request = {'initial': {'raw': 1}, 'final': {'done': 1}, 'capacities': {'dead': 3, 'done': 3, 'mid': 3, 'raw': 3}, 'transitions': [{'id': 'a_dead', 'label': 'x', 'consume': {'raw': 1}, 'produce': {'dead': 1}, 'model_cost': 1}, {'id': 'z_live', 'label': 'x', 'consume': {'raw': 1}, 'produce': {'mid': 1}, 'model_cost': 4}, {'id': 'finish', 'label': 'y', 'consume': {'mid': 1}, 'produce': {'done': 1}, 'model_cost': 1}], 'groups': [[{'id': 'x', 'label': 'x', 'skip_cost': 5}], [{'id': 'y', 'label': 'y', 'skip_cost': 5}]]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'cost': 0, 'alignment': [{'kind': 'sync', 'event': 'x', 'transition': 'z_live'}, {'kind': 'sync', 'event': 'y', 'transition': 'finish'}], 'log_moves': 0, 'model_moves': 0, 'synchronous_moves': 2}
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
