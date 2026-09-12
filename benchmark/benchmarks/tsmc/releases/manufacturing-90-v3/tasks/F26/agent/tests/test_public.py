import copy
import pytest
from fabops.domain import run


def test_single_lifecycle():
    request = {'events': [{'id': 's', 'kind': 'start', 'time': 1, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}, {'id': 'c', 'kind': 'complete', 'time': 4, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 1, 'alternatives': 1, 'certain_pairs': [['s', 'c']], 'certain_unmatched': [], 'duration_bounds': [3, 3]}
    assert request == before

def test_overlapping_runs_are_ambiguous():
    request = {'events': [{'id': 's1', 'kind': 'start', 'time': 0, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}, {'id': 's2', 'kind': 'start', 'time': 1, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}, {'id': 'c1', 'kind': 'complete', 'time': 3, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}, {'id': 'c2', 'kind': 'complete', 'time': 4, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 2, 'alternatives': 2, 'certain_pairs': [], 'certain_unmatched': [], 'duration_bounds': [6, 6]}
    assert request == before

def test_known_run_ids_force_cross_order():
    request = {'events': [{'id': 's1', 'kind': 'start', 'time': 0, 'case': 'lot', 'activity': 'etch', 'resource': 'tool', 'run': 'b'}, {'id': 's2', 'kind': 'start', 'time': 1, 'case': 'lot', 'activity': 'etch', 'resource': 'tool', 'run': 'a'}, {'id': 'c1', 'kind': 'complete', 'time': 3, 'case': 'lot', 'activity': 'etch', 'resource': 'tool', 'run': 'a'}, {'id': 'c2', 'kind': 'complete', 'time': 5, 'case': 'lot', 'activity': 'etch', 'resource': 'tool', 'run': 'b'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 2, 'alternatives': 1, 'certain_pairs': [['s1', 'c2'], ['s2', 'c1']], 'certain_unmatched': [], 'duration_bounds': [7, 7]}
    assert request == before

def test_transport_retries_are_not_operations():
    request = {'events': [{'id': 's', 'kind': 'start', 'time': 1, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}, {'id': 's', 'kind': 'start', 'time': 1, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}, {'id': 'c', 'kind': 'complete', 'time': 4, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}, {'id': 'c', 'kind': 'complete', 'time': 4, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 1, 'alternatives': 1, 'certain_pairs': [['s', 'c']], 'certain_unmatched': [], 'duration_bounds': [3, 3]}
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
