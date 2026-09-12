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

def test_capacity_reduces_maximum():
    request = {'events': [{'id': 'as', 'kind': 'start', 'time': 0, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'a', 'units': 1}, {'id': 'ae', 'kind': 'complete', 'time': 3, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'a'}, {'id': 'bs', 'kind': 'start', 'time': 1, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'b', 'units': 1}, {'id': 'be', 'kind': 'complete', 'time': 2, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'b'}], 'capacities': {'m': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 1, 'alternatives': 2, 'certain_pairs': [], 'certain_unmatched': [], 'duration_bounds': [1, 3]}
    assert request == before

def test_coupled_excludes_all():
    request = {'events': [{'id': 'as', 'kind': 'start', 'time': 0, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'a', 'units': 1}, {'id': 'ae', 'kind': 'complete', 'time': 3, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'a'}, {'id': 'bs', 'kind': 'start', 'time': 1, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'b', 'units': 1}, {'id': 'be', 'kind': 'complete', 'time': 2, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'b'}], 'capacities': {'m': 1}, 'coupled': [['as', 'bs']]}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 0, 'alternatives': 1, 'certain_pairs': [], 'certain_unmatched': ['ae', 'as', 'be', 'bs'], 'duration_bounds': [0, 0]}
    assert request == before

def test_coupled_requires_complete_search():
    request = {'events': [{'id': 'as', 'kind': 'start', 'time': 0, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'a', 'units': 1}, {'id': 'ae', 'kind': 'complete', 'time': 3, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'a'}, {'id': 'bs', 'kind': 'start', 'time': 1, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'b', 'units': 1}, {'id': 'be', 'kind': 'complete', 'time': 2, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'b'}], 'capacities': {'m': 2}, 'coupled': [['as', 'bs']]}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 2, 'alternatives': 1, 'certain_pairs': [['as', 'ae'], ['bs', 'be']], 'certain_unmatched': [], 'duration_bounds': [4, 4]}
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
