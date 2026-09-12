import copy
import pytest
from fabops.domain import run


def test_receipt_order_drives_downstream_supply():
    request = {'initial': {'raw': 2}, 'recipes': {'move': {'consume': {'raw': 1}, 'produce': {'wip': 1}, 'scrap': 0}, 'finish': {'consume': {'wip': 1}, 'produce': {'done': 1}, 'scrap': 0}}, 'events': [{'id': 'a_finish', 'revision': 1, 'order': 2, 'recipe': 'finish', 'batches': 2}, {'id': 'z_move', 'revision': 1, 'order': 1, 'recipe': 'move', 'batches': 2}], 'capacities': {'done': 20, 'raw': 20, 'wip': 20}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'raw': 0, 'wip': 0, 'done': 2}, 'accepted': ['z_move', 'a_finish'], 'rejected': [], 'scrap': 0}
    assert request == before

def test_partial_gate_shortage_preserves_all_inputs():
    request = {'initial': {'a': 2, 'b': 0}, 'recipes': {'join': {'consume': {'a': 1, 'b': 1}, 'produce': {'done': 2}, 'scrap': 0}}, 'events': [{'id': 'join', 'revision': 1, 'order': 1, 'recipe': 'join', 'batches': 1}], 'capacities': {'a': 20, 'b': 20, 'done': 20}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'a': 2, 'b': 0, 'done': 0}, 'accepted': [], 'rejected': ['join'], 'scrap': 0}
    assert request == before

def test_late_correction_removes_downstream_supply():
    request = {'initial': {'raw': 2}, 'recipes': {'move': {'consume': {'raw': 1}, 'produce': {'wip': 1}, 'scrap': 0}, 'finish': {'consume': {'wip': 1}, 'produce': {'done': 1}, 'scrap': 0}}, 'events': [{'id': 'a_move', 'revision': 2, 'order': 1, 'recipe': 'move', 'batches': 1}, {'id': 'a_move', 'revision': 1, 'order': 1, 'recipe': 'move', 'batches': 2}, {'id': 'b_finish', 'revision': 1, 'order': 2, 'recipe': 'finish', 'batches': 2}], 'capacities': {'done': 20, 'raw': 20, 'wip': 20}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'raw': 1, 'wip': 1, 'done': 0}, 'accepted': ['a_move'], 'rejected': ['b_finish'], 'scrap': 0}
    assert request == before

def test_capacity_rejection_rolls_back_consumption():
    request = {'initial': {'raw': 2}, 'recipes': {'move': {'consume': {'raw': 1}, 'produce': {'wip': 1}, 'scrap': 0}, 'finish': {'consume': {'wip': 1}, 'produce': {'done': 1}, 'scrap': 0}}, 'events': [{'id': 'a_block', 'revision': 1, 'order': 0, 'recipe': 'move', 'batches': 2}, {'id': 'b_retry', 'revision': 1, 'order': 1, 'recipe': 'move', 'batches': 1}], 'capacities': {'raw': 2, 'wip': 1, 'done': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'raw': 1, 'wip': 1, 'done': 0}, 'accepted': ['b_retry'], 'rejected': ['a_block'], 'scrap': 0}
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
