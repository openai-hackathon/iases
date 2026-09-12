import copy
import pytest
from fabops.domain import run


def test_weighted_self_loop():
    request = {'initial': {'p': 2}, 'final': {'p': 2}, 'capacities': {'p': 2}, 'transitions': [{'id': 'batch', 'label': 'b', 'consume': {'p': 2}, 'produce': {'p': 2}, 'model_cost': 2}], 'groups': [[{'id': 'b', 'label': 'b', 'skip_cost': 5}]]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'cost': 0, 'alignment': [{'kind': 'sync', 'event': 'b', 'transition': 'batch'}], 'log_moves': 0, 'model_moves': 0, 'synchronous_moves': 1}
    assert request == before

def test_weighted_consumption():
    request = {'initial': {'raw': 2}, 'final': {'done': 1}, 'capacities': {'done': 3, 'raw': 3}, 'transitions': [{'id': 'batch', 'label': 'b', 'consume': {'raw': 2}, 'produce': {'done': 1}, 'model_cost': 2}], 'groups': [[{'id': 'b', 'label': 'b', 'skip_cost': 5}]]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'cost': 0, 'alignment': [{'kind': 'sync', 'event': 'b', 'transition': 'batch'}], 'log_moves': 0, 'model_moves': 0, 'synchronous_moves': 1}
    assert request == before

def test_weighted_production():
    request = {'initial': {'raw': 1}, 'final': {'done': 2}, 'capacities': {'done': 3, 'raw': 3}, 'transitions': [{'id': 'split', 'label': 's', 'consume': {'raw': 1}, 'produce': {'done': 2}, 'model_cost': 2}], 'groups': [[{'id': 's', 'label': 's', 'skip_cost': 5}]]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'cost': 0, 'alignment': [{'kind': 'sync', 'event': 's', 'transition': 'split'}], 'log_moves': 0, 'model_moves': 0, 'synchronous_moves': 1}
    assert request == before

def test_unavailable_weight():
    request = {'initial': {'raw': 1}, 'final': {'done': 1}, 'capacities': {'done': 3, 'raw': 3}, 'transitions': [{'id': 'batch', 'label': 'b', 'consume': {'raw': 2}, 'produce': {'done': 1}, 'model_cost': 2}], 'groups': [[{'id': 'b', 'label': 'b', 'skip_cost': 5}]]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': False, 'cost': None, 'alignment': [], 'log_moves': 0, 'model_moves': 0, 'synchronous_moves': 0}
    assert request == before

def test_leftover_forbidden():
    request = {'initial': {'raw': 1, 'hold': 1}, 'final': {'done': 1}, 'capacities': {'done': 3, 'hold': 3, 'raw': 3}, 'transitions': [{'id': 'work', 'label': 'work', 'consume': {'raw': 1}, 'produce': {'done': 1}, 'model_cost': 2}], 'groups': [[{'id': 'w', 'label': 'work', 'skip_cost': 5}]]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': False, 'cost': None, 'alignment': [], 'log_moves': 0, 'model_moves': 0, 'synchronous_moves': 0}
    assert request == before

def test_trailing_silent_cleanup():
    request = {'initial': {'raw': 1}, 'final': {'done': 1}, 'capacities': {'done': 3, 'mid': 3, 'raw': 3}, 'transitions': [{'id': 'work', 'label': 'w', 'consume': {'raw': 1}, 'produce': {'mid': 1}, 'model_cost': 2}, {'id': 'clean', 'label': None, 'consume': {'mid': 1}, 'produce': {'done': 1}, 'model_cost': 3}], 'groups': [[{'id': 'w', 'label': 'w', 'skip_cost': 5}]]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'cost': 3, 'alignment': [{'kind': 'sync', 'event': 'w', 'transition': 'work'}, {'kind': 'model', 'event': None, 'transition': 'clean'}], 'log_moves': 0, 'model_moves': 1, 'synchronous_moves': 1}
    assert request == before

def test_leading_silent_route():
    request = {'initial': {'raw': 1}, 'final': {'done': 1}, 'capacities': {'done': 3, 'mid': 3, 'raw': 3}, 'transitions': [{'id': 'route', 'label': None, 'consume': {'raw': 1}, 'produce': {'mid': 1}, 'model_cost': 3}, {'id': 'work', 'label': 'w', 'consume': {'mid': 1}, 'produce': {'done': 1}, 'model_cost': 2}], 'groups': [[{'id': 'w', 'label': 'w', 'skip_cost': 5}]]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'cost': 3, 'alignment': [{'kind': 'model', 'event': None, 'transition': 'route'}, {'kind': 'sync', 'event': 'w', 'transition': 'work'}], 'log_moves': 0, 'model_moves': 1, 'synchronous_moves': 1}
    assert request == before

def test_visible_model_step():
    request = {'initial': {'raw': 1}, 'final': {'done': 1}, 'capacities': {'done': 3, 'mid': 3, 'raw': 3}, 'transitions': [{'id': 'first', 'label': 'a', 'consume': {'raw': 1}, 'produce': {'mid': 1}, 'model_cost': 2}, {'id': 'second', 'label': 'b', 'consume': {'mid': 1}, 'produce': {'done': 1}, 'model_cost': 2}], 'groups': [[{'id': 'b', 'label': 'b', 'skip_cost': 5}]]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'cost': 2, 'alignment': [{'kind': 'model', 'event': None, 'transition': 'first'}, {'kind': 'sync', 'event': 'b', 'transition': 'second'}], 'log_moves': 0, 'model_moves': 1, 'synchronous_moves': 1}
    assert request == before

def test_skip_only():
    request = {'initial': {'p': 1}, 'final': {'p': 1}, 'capacities': {'p': 3}, 'transitions': [], 'groups': [[{'id': 'noise', 'label': 'n', 'skip_cost': 7}]]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'cost': 7, 'alignment': [{'kind': 'log', 'event': 'noise', 'transition': None}], 'log_moves': 1, 'model_moves': 0, 'synchronous_moves': 0}
    assert request == before

def test_empty_complete():
    request = {'initial': {'p': 1}, 'final': {'p': 1}, 'capacities': {'p': 3}, 'transitions': [], 'groups': []}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'cost': 0, 'alignment': [], 'log_moves': 0, 'model_moves': 0, 'synchronous_moves': 0}
    assert request == before

def test_empty_unreachable():
    request = {'initial': {'raw': 1}, 'final': {'done': 1}, 'capacities': {'done': 3, 'raw': 3}, 'transitions': [], 'groups': []}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': False, 'cost': None, 'alignment': [], 'log_moves': 0, 'model_moves': 0, 'synchronous_moves': 0}
    assert request == before

def test_skip_after_completion():
    request = {'initial': {'raw': 1}, 'final': {'done': 1}, 'capacities': {'done': 3, 'raw': 3}, 'transitions': [{'id': 'work', 'label': 'work', 'consume': {'raw': 1}, 'produce': {'done': 1}, 'model_cost': 2}], 'groups': [[{'id': 'w', 'label': 'work', 'skip_cost': 5}], [{'id': 'z', 'label': 'noise', 'skip_cost': 4}]]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'cost': 4, 'alignment': [{'kind': 'sync', 'event': 'w', 'transition': 'work'}, {'kind': 'log', 'event': 'z', 'transition': None}], 'log_moves': 1, 'model_moves': 0, 'synchronous_moves': 1}
    assert request == before

def test_ordered_groups_cannot_reverse():
    request = {'initial': {'raw': 1}, 'final': {'done': 1}, 'capacities': {'done': 3, 'mid': 3, 'raw': 3}, 'transitions': [{'id': 'first', 'label': 'a', 'consume': {'raw': 1}, 'produce': {'mid': 1}, 'model_cost': 2}, {'id': 'second', 'label': 'b', 'consume': {'mid': 1}, 'produce': {'done': 1}, 'model_cost': 2}], 'groups': [[{'id': 'b', 'label': 'b', 'skip_cost': 1}], [{'id': 'a', 'label': 'a', 'skip_cost': 7}]]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'cost': 3, 'alignment': [{'kind': 'log', 'event': 'b', 'transition': None}, {'kind': 'sync', 'event': 'a', 'transition': 'first'}, {'kind': 'model', 'event': None, 'transition': 'second'}], 'log_moves': 1, 'model_moves': 1, 'synchronous_moves': 1}
    assert request == before

def test_same_group_extra_event():
    request = {'initial': {'raw': 1}, 'final': {'done': 1}, 'capacities': {'done': 3, 'mid': 3, 'raw': 3}, 'transitions': [{'id': 'first', 'label': 'a', 'consume': {'raw': 1}, 'produce': {'mid': 1}, 'model_cost': 2}, {'id': 'second', 'label': 'b', 'consume': {'mid': 1}, 'produce': {'done': 1}, 'model_cost': 2}], 'groups': [[{'id': 'b', 'label': 'b', 'skip_cost': 5}, {'id': 'noise', 'label': 'n', 'skip_cost': 3}, {'id': 'a', 'label': 'a', 'skip_cost': 5}]]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'cost': 3, 'alignment': [{'kind': 'log', 'event': 'noise', 'transition': None}, {'kind': 'sync', 'event': 'a', 'transition': 'first'}, {'kind': 'sync', 'event': 'b', 'transition': 'second'}], 'log_moves': 1, 'model_moves': 0, 'synchronous_moves': 2}
    assert request == before

def test_duplicate_activity_occurrences():
    request = {'initial': {'raw': 1}, 'final': {'done': 1}, 'capacities': {'done': 3, 'mid': 3, 'raw': 3}, 'transitions': [{'id': 'a', 'label': 'x', 'consume': {'raw': 1}, 'produce': {'mid': 1}, 'model_cost': 2}, {'id': 'b', 'label': 'x', 'consume': {'mid': 1}, 'produce': {'done': 1}, 'model_cost': 2}], 'groups': [[{'id': 'z', 'label': 'x', 'skip_cost': 5}, {'id': 'a', 'label': 'x', 'skip_cost': 5}]]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'cost': 0, 'alignment': [{'kind': 'sync', 'event': 'a', 'transition': 'a'}, {'kind': 'sync', 'event': 'z', 'transition': 'b'}], 'log_moves': 0, 'model_moves': 0, 'synchronous_moves': 2}
    assert request == before

def test_transition_tie_by_id():
    request = {'initial': {'raw': 1}, 'final': {'done': 1}, 'capacities': {'done': 3, 'raw': 3}, 'transitions': [{'id': 'z', 'label': 'work', 'consume': {'raw': 1}, 'produce': {'done': 1}, 'model_cost': 2}, {'id': 'a', 'label': 'work', 'consume': {'raw': 1}, 'produce': {'done': 1}, 'model_cost': 2}], 'groups': [[{'id': 'w', 'label': 'work', 'skip_cost': 5}]]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'cost': 0, 'alignment': [{'kind': 'sync', 'event': 'w', 'transition': 'a'}], 'log_moves': 0, 'model_moves': 0, 'synchronous_moves': 1}
    assert request == before

def test_globally_cheaper_model_route():
    request = {'initial': {'raw': 1}, 'final': {'done': 1}, 'capacities': {'done': 3, 'mid': 3, 'raw': 3}, 'transitions': [{'id': 'cheap', 'label': None, 'consume': {'raw': 1}, 'produce': {'mid': 1}, 'model_cost': 1}, {'id': 'expensive', 'label': None, 'consume': {'mid': 1}, 'produce': {'done': 1}, 'model_cost': 9}, {'id': 'direct', 'label': None, 'consume': {'raw': 1}, 'produce': {'done': 1}, 'model_cost': 4}], 'groups': []}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'cost': 4, 'alignment': [{'kind': 'model', 'event': None, 'transition': 'direct'}], 'log_moves': 0, 'model_moves': 1, 'synchronous_moves': 0}
    assert request == before

def test_same_cost_shortest_witness():
    request = {'initial': {'raw': 1}, 'final': {'done': 1}, 'capacities': {'done': 3, 'mid': 3, 'raw': 3}, 'transitions': [{'id': 'a', 'label': None, 'consume': {'raw': 1}, 'produce': {'mid': 1}, 'model_cost': 1}, {'id': 'b', 'label': None, 'consume': {'mid': 1}, 'produce': {'done': 1}, 'model_cost': 1}, {'id': 'z', 'label': None, 'consume': {'raw': 1}, 'produce': {'done': 1}, 'model_cost': 2}], 'groups': []}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'cost': 2, 'alignment': [{'kind': 'model', 'event': None, 'transition': 'z'}], 'log_moves': 0, 'model_moves': 1, 'synchronous_moves': 0}
    assert request == before

def test_relax_previously_discovered_state():
    request = {'initial': {'raw': 1}, 'final': {'done': 1}, 'capacities': {'done': 3, 'mid': 3, 'raw': 3}, 'transitions': [{'id': 'direct', 'label': None, 'consume': {'raw': 1}, 'produce': {'done': 1}, 'model_cost': 8}, {'id': 'a', 'label': None, 'consume': {'raw': 1}, 'produce': {'mid': 1}, 'model_cost': 1}, {'id': 'b', 'label': None, 'consume': {'mid': 1}, 'produce': {'done': 1}, 'model_cost': 1}], 'groups': []}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'cost': 2, 'alignment': [{'kind': 'model', 'event': None, 'transition': 'a'}, {'kind': 'model', 'event': None, 'transition': 'b'}], 'log_moves': 0, 'model_moves': 2, 'synchronous_moves': 0}
    assert request == before

def test_positive_silent_cycle():
    request = {'initial': {'raw': 1}, 'final': {'done': 1}, 'capacities': {'done': 3, 'raw': 3}, 'transitions': [{'id': 'a_cycle', 'label': None, 'consume': {'raw': 1}, 'produce': {'raw': 1}, 'model_cost': 1}, {'id': 'finish', 'label': None, 'consume': {'raw': 1}, 'produce': {'done': 1}, 'model_cost': 3}], 'groups': []}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'cost': 3, 'alignment': [{'kind': 'model', 'event': None, 'transition': 'finish'}], 'log_moves': 0, 'model_moves': 1, 'synchronous_moves': 0}
    assert request == before

def test_parallel_join():
    request = {'initial': {'raw': 1}, 'final': {'done': 1}, 'capacities': {'a': 3, 'a_done': 3, 'b': 3, 'b_done': 3, 'done': 3, 'raw': 3}, 'transitions': [{'id': 'split', 'label': None, 'consume': {'raw': 1}, 'produce': {'a': 1, 'b': 1}, 'model_cost': 2}, {'id': 'a', 'label': 'a', 'consume': {'a': 1}, 'produce': {'a_done': 1}, 'model_cost': 2}, {'id': 'b', 'label': 'b', 'consume': {'b': 1}, 'produce': {'b_done': 1}, 'model_cost': 2}, {'id': 'join', 'label': None, 'consume': {'a_done': 1, 'b_done': 1}, 'produce': {'done': 1}, 'model_cost': 3}], 'groups': [[{'id': 'eb', 'label': 'b', 'skip_cost': 5}, {'id': 'ea', 'label': 'a', 'skip_cost': 5}]]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'cost': 5, 'alignment': [{'kind': 'model', 'event': None, 'transition': 'split'}, {'kind': 'sync', 'event': 'ea', 'transition': 'a'}, {'kind': 'sync', 'event': 'eb', 'transition': 'b'}, {'kind': 'model', 'event': None, 'transition': 'join'}], 'log_moves': 0, 'model_moves': 2, 'synchronous_moves': 2}
    assert request == before

def test_skip_cheaper_than_wrong_matching_path():
    request = {'initial': {'raw': 1}, 'final': {'done': 1}, 'capacities': {'done': 3, 'mid': 3, 'raw': 3}, 'transitions': [{'id': 'wrong', 'label': 'x', 'consume': {'raw': 1}, 'produce': {'mid': 1}, 'model_cost': 2}, {'id': 'cleanup', 'label': None, 'consume': {'mid': 1}, 'produce': {'done': 1}, 'model_cost': 20}, {'id': 'direct', 'label': None, 'consume': {'raw': 1}, 'produce': {'done': 1}, 'model_cost': 2}], 'groups': [[{'id': 'x', 'label': 'x', 'skip_cost': 1}]]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'cost': 3, 'alignment': [{'kind': 'log', 'event': 'x', 'transition': None}, {'kind': 'model', 'event': None, 'transition': 'direct'}], 'log_moves': 1, 'model_moves': 1, 'synchronous_moves': 0}
    assert request == before

def test_group_identity_changes_future_cost():
    request = {'initial': {'raw': 1}, 'final': {'done': 1}, 'capacities': {'done': 3, 'raw': 3}, 'transitions': [{'id': 'a', 'label': 'x', 'consume': {'raw': 1}, 'produce': {'done': 1}, 'model_cost': 2}], 'groups': [[{'id': 'cheap', 'label': 'x', 'skip_cost': 1}, {'id': 'costly', 'label': 'x', 'skip_cost': 9}]]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'cost': 1, 'alignment': [{'kind': 'log', 'event': 'cheap', 'transition': None}, {'kind': 'sync', 'event': 'costly', 'transition': 'a'}], 'log_moves': 1, 'model_moves': 0, 'synchronous_moves': 1}
    assert request == before

def test_full_group_consumption():
    request = {'initial': {'raw': 1}, 'final': {'done': 1}, 'capacities': {'done': 3, 'raw': 3}, 'transitions': [{'id': 'work', 'label': 'work', 'consume': {'raw': 1}, 'produce': {'done': 1}, 'model_cost': 2}], 'groups': [[{'id': 'w', 'label': 'work', 'skip_cost': 5}, {'id': 'a', 'label': 'noise', 'skip_cost': 2}, {'id': 'b', 'label': 'noise', 'skip_cost': 3}, {'id': 'c', 'label': 'noise', 'skip_cost': 4}]]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'cost': 9, 'alignment': [{'kind': 'log', 'event': 'a', 'transition': None}, {'kind': 'log', 'event': 'b', 'transition': None}, {'kind': 'log', 'event': 'c', 'transition': None}, {'kind': 'sync', 'event': 'w', 'transition': 'work'}], 'log_moves': 3, 'model_moves': 0, 'synchronous_moves': 1}
    assert request == before

def test_capacity_blocks_route():
    request = {'initial': {'raw': 1}, 'final': {'done': 1}, 'capacities': {'raw': 1, 'done': 1}, 'transitions': [{'id': 'work', 'label': 'w', 'consume': {'raw': 1}, 'produce': {'done': 2}, 'model_cost': 2}], 'groups': [[{'id': 'w', 'label': 'w', 'skip_cost': 5}]]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': False, 'cost': None, 'alignment': [], 'log_moves': 0, 'model_moves': 0, 'synchronous_moves': 0}
    assert request == before

def test_bounded_ambiguous_repetition():
    request = {'initial': {'p': 1}, 'final': {'p': 1}, 'capacities': {'p': 1}, 'transitions': [{'id': 'work', 'label': 'w', 'consume': {'p': 1}, 'produce': {'p': 1}, 'model_cost': 2}, {'id': 'cycle', 'label': None, 'consume': {'p': 1}, 'produce': {'p': 1}, 'model_cost': 1}], 'groups': [[{'id': 'e3', 'label': 'w', 'skip_cost': 5}, {'id': 'e2', 'label': 'w', 'skip_cost': 5}, {'id': 'e1', 'label': 'w', 'skip_cost': 5}, {'id': 'e0', 'label': 'w', 'skip_cost': 5}], [{'id': 'e7', 'label': 'w', 'skip_cost': 5}, {'id': 'e6', 'label': 'w', 'skip_cost': 5}, {'id': 'e5', 'label': 'w', 'skip_cost': 5}, {'id': 'e4', 'label': 'w', 'skip_cost': 5}], [{'id': 'e9', 'label': 'w', 'skip_cost': 5}, {'id': 'e8', 'label': 'w', 'skip_cost': 5}]]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'cost': 0, 'alignment': [{'kind': 'sync', 'event': 'e0', 'transition': 'work'}, {'kind': 'sync', 'event': 'e1', 'transition': 'work'}, {'kind': 'sync', 'event': 'e2', 'transition': 'work'}, {'kind': 'sync', 'event': 'e3', 'transition': 'work'}, {'kind': 'sync', 'event': 'e4', 'transition': 'work'}, {'kind': 'sync', 'event': 'e5', 'transition': 'work'}, {'kind': 'sync', 'event': 'e6', 'transition': 'work'}, {'kind': 'sync', 'event': 'e7', 'transition': 'work'}, {'kind': 'sync', 'event': 'e8', 'transition': 'work'}, {'kind': 'sync', 'event': 'e9', 'transition': 'work'}], 'log_moves': 0, 'model_moves': 0, 'synchronous_moves': 10}
    assert request == before

def test_full_256_marking_domain_with_event_ambiguity():
    request = {'initial': {}, 'final': {'a': 3, 'b': 3, 'c': 3, 'd': 3}, 'capacities': {'a': 3, 'b': 3, 'c': 3, 'd': 3}, 'transitions': [{'id': 'a', 'label': 'fill', 'consume': {}, 'produce': {'a': 1}, 'model_cost': 1}, {'id': 'b', 'label': 'fill', 'consume': {}, 'produce': {'b': 1}, 'model_cost': 1}, {'id': 'c', 'label': 'fill', 'consume': {}, 'produce': {'c': 1}, 'model_cost': 1}, {'id': 'd', 'label': 'fill', 'consume': {}, 'produce': {'d': 1}, 'model_cost': 1}, {'id': 'drain_a', 'label': None, 'consume': {'a': 1}, 'produce': {}, 'model_cost': 1}, {'id': 'drain_b', 'label': None, 'consume': {'b': 1}, 'produce': {}, 'model_cost': 1}, {'id': 'drain_c', 'label': None, 'consume': {'c': 1}, 'produce': {}, 'model_cost': 1}, {'id': 'drain_d', 'label': None, 'consume': {'d': 1}, 'produce': {}, 'model_cost': 1}], 'groups': [[{'id': 'e3', 'label': 'fill', 'skip_cost': 5}, {'id': 'e1', 'label': 'fill', 'skip_cost': 5}, {'id': 'e0', 'label': 'fill', 'skip_cost': 5}, {'id': 'e2', 'label': 'fill', 'skip_cost': 5}], [{'id': 'e7', 'label': 'fill', 'skip_cost': 5}, {'id': 'e5', 'label': 'fill', 'skip_cost': 5}, {'id': 'e4', 'label': 'fill', 'skip_cost': 5}, {'id': 'e6', 'label': 'fill', 'skip_cost': 5}], [{'id': 'e9', 'label': 'fill', 'skip_cost': 5}, {'id': 'e8', 'label': 'fill', 'skip_cost': 5}]]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': True, 'cost': 2, 'alignment': [{'kind': 'model', 'event': None, 'transition': 'a'}, {'kind': 'model', 'event': None, 'transition': 'a'}, {'kind': 'sync', 'event': 'e0', 'transition': 'a'}, {'kind': 'sync', 'event': 'e1', 'transition': 'b'}, {'kind': 'sync', 'event': 'e2', 'transition': 'b'}, {'kind': 'sync', 'event': 'e3', 'transition': 'b'}, {'kind': 'sync', 'event': 'e4', 'transition': 'c'}, {'kind': 'sync', 'event': 'e5', 'transition': 'c'}, {'kind': 'sync', 'event': 'e6', 'transition': 'c'}, {'kind': 'sync', 'event': 'e7', 'transition': 'd'}, {'kind': 'sync', 'event': 'e8', 'transition': 'd'}, {'kind': 'sync', 'event': 'e9', 'transition': 'd'}], 'log_moves': 0, 'model_moves': 2, 'synchronous_moves': 10}
    assert request == before

def test_small_acyclic_alignments_against_exhaustive_histories():
    import random
    rng = random.Random(2502)
    for trial in range(60):
        # Acyclic one-token processes make exhaustive history enumeration finite;
        # this oracle has no priority queue, marking cache or production helpers.
        transitions = [dict(id=name, label=rng.choice([None, "a", "b"]),
                            consume={start:1}, produce={end:1}, model_cost=rng.randint(1,6))
                       for name,start,end in [("left","p0","p1"),("right","p1","p2"),("direct","p0","p2")]]
        events = [dict(id=f"e{i}",label=rng.choice(["a","b"]),skip_cost=rng.randint(1,6))
                  for i in range(3)]
        groups = [events] if trial % 2 else [events[:1],events[1:]]
        request = dict(capacities={"p0":1,"p1":1,"p2":1}, initial={"p0":1}, final={"p2":1},
                       transitions=transitions, groups=groups)
        before = copy.deepcopy(request)
        candidates = []
        all_ids = {e["id"] for e in events}
        def visit(place, consumed, cost, moves):
            if consumed == all_ids and place == "p2":
                candidates.append((cost,len(moves),moves))
                return
            active = []
            for group in groups:
                active = [e for e in group if e["id"] not in consumed]
                if active:
                    break
            for event in active:
                visit(place, consumed | {event["id"]}, cost+event["skip_cost"],
                      moves+(("log",event["id"],""),))
            for t in transitions:
                if place not in t["consume"]:
                    continue
                target = next(iter(t["produce"]))
                visit(target, consumed, cost+t["model_cost"], moves+(("model","",t["id"]),))
                for event in active:
                    if event["label"] == t["label"]:
                        visit(target, consumed | {event["id"]}, cost,
                              moves+(("sync",event["id"],t["id"]),))
        visit("p0",set(),0,())
        cost, _, moves = min(candidates)
        expected = dict(accepted=True,cost=cost,
                        alignment=[dict(kind=k,event=e or None,transition=t or None) for k,e,t in moves],
                        log_moves=sum(k=="log" for k,_,_ in moves),
                        model_moves=sum(k=="model" for k,_,_ in moves),
                        synchronous_moves=sum(k=="sync" for k,_,_ in moves))
        assert run(request) == expected
        assert request == before
