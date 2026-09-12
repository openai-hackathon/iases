import copy
import pytest
from fabops.domain import run


def test_empty_trace_exact_marking():
    request = {'capacities': {'p': 3}, 'initial': {'p': 1}, 'final': {'p': 1}, 'transitions': [], 'trace': []}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'witness': [], 'silent': 0, 'marking': {'p': 1}}
    assert request == before

def test_empty_trace_mismatch():
    request = {'capacities': {'p': 3}, 'initial': {'p': 1}, 'final': {}, 'transitions': [], 'trace': []}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': False, 'witness': [], 'silent': None, 'marking': {'p': 1}}
    assert request == before

def test_unmatched_activity():
    request = {'capacities': {'done': 3, 'raw': 3}, 'initial': {'raw': 1}, 'final': {'done': 1}, 'transitions': [{'id': 'etch', 'label': 'etch', 'consume': {'raw': 1}, 'produce': {'done': 1}}], 'trace': ['polish']}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': False, 'witness': [], 'silent': None, 'marking': {'done': 0, 'raw': 1}}
    assert request == before

def test_weighted_self_loop_available():
    request = {'capacities': {'p': 3}, 'initial': {'p': 2}, 'final': {'p': 2}, 'transitions': [{'id': 'batch', 'label': 'inspect', 'consume': {'p': 2}, 'produce': {'p': 2}}], 'trace': ['inspect', 'inspect']}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'witness': ['batch', 'batch'], 'silent': 0, 'marking': {'p': 2}}
    assert request == before

def test_transient_capacity_overflow():
    request = {'capacities': {'p': 1, 'q': 1, 'done': 1}, 'initial': {'p': 1}, 'final': {'done': 1}, 'transitions': [{'id': 'grow', 'label': None, 'consume': {'p': 1}, 'produce': {'q': 2}}, {'id': 'trim', 'label': 'trim', 'consume': {'q': 2}, 'produce': {'done': 1}}], 'trace': ['trim']}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': False, 'witness': [], 'silent': None, 'marking': {'done': 0, 'p': 1, 'q': 0}}
    assert request == before

def test_capacity_after_consumption():
    request = {'capacities': {'p': 2}, 'initial': {'p': 2}, 'final': {'p': 2}, 'transitions': [{'id': 'batch', 'label': 'inspect', 'consume': {'p': 2}, 'produce': {'p': 2}}], 'trace': ['inspect']}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'witness': ['batch'], 'silent': 0, 'marking': {'p': 2}}
    assert request == before

def test_same_label_requires_lookahead():
    request = {'capacities': {'dead': 3, 'done': 3, 'p': 3, 'q': 3}, 'initial': {'p': 1}, 'final': {'done': 1}, 'transitions': [{'id': 'a_dead', 'label': 'work', 'consume': {'p': 1}, 'produce': {'dead': 1}}, {'id': 'z_live', 'label': 'work', 'consume': {'p': 1}, 'produce': {'q': 1}}, {'id': 'finish', 'label': 'finish', 'consume': {'q': 1}, 'produce': {'done': 1}}], 'trace': ['work', 'finish']}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'witness': ['z_live', 'finish'], 'silent': 0, 'marking': {'dead': 0, 'done': 1, 'p': 0, 'q': 0}}
    assert request == before

def test_silent_cost_before_lexical_tie():
    request = {'capacities': {'done': 3, 'p': 3, 'q': 3}, 'initial': {'p': 1}, 'final': {'done': 1}, 'transitions': [{'id': 'a_detour', 'label': None, 'consume': {'p': 1}, 'produce': {'q': 1}}, {'id': 'b_work', 'label': 'work', 'consume': {'q': 1}, 'produce': {'done': 1}}, {'id': 'z_direct', 'label': 'work', 'consume': {'p': 1}, 'produce': {'done': 1}}], 'trace': ['work']}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'witness': ['z_direct'], 'silent': 0, 'marking': {'done': 1, 'p': 0, 'q': 0}}
    assert request == before

def test_lexical_witness_tie():
    request = {'capacities': {'done': 3, 'p': 3, 'q': 3}, 'initial': {'p': 1}, 'final': {'done': 1}, 'transitions': [{'id': 'z_route', 'label': None, 'consume': {'p': 1}, 'produce': {'q': 1}}, {'id': 'a_route', 'label': None, 'consume': {'p': 1}, 'produce': {'q': 1}}, {'id': 'work', 'label': 'work', 'consume': {'q': 1}, 'produce': {'done': 1}}], 'trace': ['work']}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'witness': ['a_route', 'work'], 'silent': 1, 'marking': {'done': 1, 'p': 0, 'q': 0}}
    assert request == before

def test_silent_cycle_terminates():
    request = {'capacities': {'done': 3, 'p': 3}, 'initial': {'p': 1}, 'final': {'done': 1}, 'transitions': [{'id': 'cycle', 'label': None, 'consume': {'p': 1}, 'produce': {'p': 1}}, {'id': 'work', 'label': 'work', 'consume': {'p': 1}, 'produce': {'done': 1}}], 'trace': ['work']}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'witness': ['work'], 'silent': 0, 'marking': {'done': 1, 'p': 0}}
    assert request == before

def test_silent_only_completion():
    request = {'capacities': {'p': 3, 'q': 3}, 'initial': {'p': 1}, 'final': {'q': 1}, 'transitions': [{'id': 'move', 'label': None, 'consume': {'p': 1}, 'produce': {'q': 1}}], 'trace': []}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'witness': ['move'], 'silent': 1, 'marking': {'p': 0, 'q': 1}}
    assert request == before

def test_join_missing_branch():
    request = {'capacities': {'a': 3, 'a_done': 3, 'b': 3, 'b_done': 3, 'done': 3, 'raw': 3}, 'initial': {'raw': 1}, 'final': {'done': 1}, 'transitions': [{'id': 'split', 'label': None, 'consume': {'raw': 1}, 'produce': {'a': 1, 'b': 1}}, {'id': 'measure', 'label': 'measure', 'consume': {'a': 1}, 'produce': {'a_done': 1}}, {'id': 'clean', 'label': 'clean', 'consume': {'b': 1}, 'produce': {'b_done': 1}}, {'id': 'join', 'label': None, 'consume': {'a_done': 1, 'b_done': 1}, 'produce': {'done': 1}}], 'trace': ['clean']}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': False, 'witness': [], 'silent': None, 'marking': {'a': 0, 'a_done': 0, 'b': 0, 'b_done': 0, 'done': 0, 'raw': 1}}
    assert request == before

def test_repeated_occurrences_with_loop():
    request = {'capacities': {'done': 3, 'p': 3, 'q': 3}, 'initial': {'p': 1}, 'final': {'done': 1}, 'transitions': [{'id': 'visit', 'label': 'work', 'consume': {'p': 1}, 'produce': {'q': 1}}, {'id': 'loop', 'label': None, 'consume': {'q': 1}, 'produce': {'p': 1}}, {'id': 'exit', 'label': 'release', 'consume': {'q': 1}, 'produce': {'done': 1}}], 'trace': ['work', 'work', 'release']}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'witness': ['visit', 'loop', 'visit', 'exit'], 'silent': 1, 'marking': {'done': 1, 'p': 0, 'q': 0}}
    assert request == before

def test_silent_split_does_not_satisfy_weighted_join():
    request = {'capacities': {'done': 3, 'p': 3, 'q': 3, 'raw': 3, 'tested': 3}, 'initial': {'raw': 1}, 'final': {'p': 1, 'done': 1}, 'transitions': [{'id': 'split', 'label': None, 'consume': {'raw': 1}, 'produce': {'p': 1, 'q': 1}}, {'id': 'inspect', 'label': 'inspect', 'consume': {'p': 2, 'q': 1}, 'produce': {'p': 2, 'tested': 1}}, {'id': 'release', 'label': 'release', 'consume': {'tested': 1}, 'produce': {'done': 1}}], 'trace': ['inspect', 'release']}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': False, 'witness': [], 'silent': None, 'marking': {'raw': 1, 'p': 0, 'q': 0, 'tested': 0, 'done': 0}}
    assert request == before

