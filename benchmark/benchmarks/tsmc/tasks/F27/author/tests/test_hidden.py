import copy
import pytest
from fabops.domain import run


def test_empty_receipts():
    request = {'initial': {'raw': 2}, 'recipes': {'move': {'consume': {'raw': 1}, 'produce': {'wip': 1}, 'scrap': 0}, 'finish': {'consume': {'wip': 1}, 'produce': {'done': 1}, 'scrap': 0}}, 'events': [], 'capacities': {'done': 20, 'raw': 20, 'wip': 20}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'raw': 2, 'wip': 0, 'done': 0}, 'accepted': [], 'rejected': [], 'scrap': 0}
    assert request == before

def test_single_receipt_control():
    request = {'initial': {'raw': 2}, 'recipes': {'move': {'consume': {'raw': 1}, 'produce': {'wip': 1}, 'scrap': 0}, 'finish': {'consume': {'wip': 1}, 'produce': {'done': 1}, 'scrap': 0}}, 'events': [{'id': 'move', 'revision': 1, 'order': 1, 'recipe': 'move', 'batches': 2}], 'capacities': {'done': 20, 'raw': 20, 'wip': 20}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'raw': 0, 'wip': 2, 'done': 0}, 'accepted': ['move'], 'rejected': [], 'scrap': 0}
    assert request == before

def test_missing_all_inputs():
    request = {'initial': {}, 'recipes': {'join': {'consume': {'a': 1, 'b': 1}, 'produce': {'done': 2}, 'scrap': 0}}, 'events': [{'id': 'join', 'revision': 1, 'order': 1, 'recipe': 'join', 'batches': 1}], 'capacities': {'a': 20, 'b': 20, 'done': 20}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'a': 0, 'b': 0, 'done': 0}, 'accepted': [], 'rejected': ['join'], 'scrap': 0}
    assert request == before

def test_complete_gate_consumes_both_branches():
    request = {'initial': {'a': 3, 'b': 2}, 'recipes': {'join': {'consume': {'a': 1, 'b': 1}, 'produce': {'done': 2}, 'scrap': 0}}, 'events': [{'id': 'join', 'revision': 1, 'order': 1, 'recipe': 'join', 'batches': 2}], 'capacities': {'a': 20, 'b': 20, 'done': 20}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'a': 1, 'b': 0, 'done': 4}, 'accepted': ['join'], 'rejected': [], 'scrap': 0}
    assert request == before

def test_tombstone_invalidates_dependent_gate():
    request = {'initial': {'raw': 2}, 'recipes': {'move': {'consume': {'raw': 1}, 'produce': {'wip': 1}, 'scrap': 0}, 'finish': {'consume': {'wip': 1}, 'produce': {'done': 1}, 'scrap': 0}}, 'events': [{'id': 'a_move', 'revision': 1, 'order': 0, 'recipe': 'move', 'batches': 2}, {'id': 'a_move', 'revision': 2, 'deleted': True}, {'id': 'b_finish', 'revision': 1, 'order': 1, 'recipe': 'finish', 'batches': 2}], 'capacities': {'done': 20, 'raw': 20, 'wip': 20}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'raw': 2, 'wip': 0, 'done': 0}, 'accepted': [], 'rejected': ['b_finish'], 'scrap': 0}
    assert request == before

def test_older_tombstone_cannot_delete_latest():
    request = {'initial': {'raw': 2}, 'recipes': {'move': {'consume': {'raw': 1}, 'produce': {'wip': 1}, 'scrap': 0}, 'finish': {'consume': {'wip': 1}, 'produce': {'done': 1}, 'scrap': 0}}, 'events': [{'id': 'a_move', 'revision': 3, 'order': 0, 'recipe': 'move', 'batches': 2}, {'id': 'a_move', 'revision': 2, 'deleted': True}], 'capacities': {'done': 20, 'raw': 20, 'wip': 20}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'raw': 0, 'wip': 2, 'done': 0}, 'accepted': ['a_move'], 'rejected': [], 'scrap': 0}
    assert request == before

def test_duplicate_revision_is_idempotent():
    request = {'initial': {'raw': 2}, 'recipes': {'move': {'consume': {'raw': 1}, 'produce': {'wip': 1}, 'scrap': 0}, 'finish': {'consume': {'wip': 1}, 'produce': {'done': 1}, 'scrap': 0}}, 'events': [{'id': 'move', 'revision': 1, 'order': 1, 'recipe': 'move', 'batches': 1}, {'id': 'move', 'revision': 1, 'order': 1, 'recipe': 'move', 'batches': 1}], 'capacities': {'done': 20, 'raw': 20, 'wip': 20}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'raw': 1, 'wip': 1, 'done': 0}, 'accepted': ['move'], 'rejected': [], 'scrap': 0}
    assert request == before

def test_conflicting_revision_rejected():
    request = {'initial': {'raw': 2}, 'recipes': {'move': {'consume': {'raw': 1}, 'produce': {'wip': 1}, 'scrap': 0}, 'finish': {'consume': {'wip': 1}, 'produce': {'done': 1}, 'scrap': 0}}, 'events': [{'id': 'move', 'revision': 1, 'order': 1, 'recipe': 'move', 'batches': 1}, {'id': 'move', 'revision': 1, 'order': 2, 'recipe': 'move', 'batches': 1}], 'capacities': {'done': 20, 'raw': 20, 'wip': 20}}
    before = copy.deepcopy(request)
    with pytest.raises(ValueError):
        run(request)
    assert request == before

def test_correction_reorders_causal_chain():
    request = {'initial': {'raw': 2}, 'recipes': {'move': {'consume': {'raw': 1}, 'produce': {'wip': 1}, 'scrap': 0}, 'finish': {'consume': {'wip': 1}, 'produce': {'done': 1}, 'scrap': 0}}, 'events': [{'id': 'a_move', 'revision': 1, 'order': 0, 'recipe': 'move', 'batches': 2}, {'id': 'b_finish', 'revision': 1, 'order': 1, 'recipe': 'finish', 'batches': 2}, {'id': 'a_move', 'revision': 2, 'order': 2, 'recipe': 'move', 'batches': 2}], 'capacities': {'done': 20, 'raw': 20, 'wip': 20}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'raw': 0, 'wip': 2, 'done': 0}, 'accepted': ['a_move'], 'rejected': ['b_finish'], 'scrap': 0}
    assert request == before

def test_equal_order_uses_logical_id():
    request = {'initial': {'raw': 1}, 'recipes': {'move': {'consume': {'raw': 1}, 'produce': {'wip': 1}, 'scrap': 0}, 'finish': {'consume': {'wip': 1}, 'produce': {'done': 1}, 'scrap': 0}}, 'events': [{'id': 'z_finish', 'revision': 1, 'order': 1, 'recipe': 'finish', 'batches': 1}, {'id': 'a_move', 'revision': 1, 'order': 1, 'recipe': 'move', 'batches': 1}], 'capacities': {'done': 20, 'raw': 20, 'wip': 20}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'raw': 0, 'wip': 0, 'done': 1}, 'accepted': ['a_move', 'z_finish'], 'rejected': [], 'scrap': 0}
    assert request == before

def test_batch_scaled_scrap():
    request = {'initial': {'raw': 9}, 'recipes': {'yield': {'consume': {'raw': 3}, 'produce': {'good': 2}, 'scrap': 1}}, 'events': [{'id': 'yield', 'revision': 1, 'order': 0, 'recipe': 'yield', 'batches': 3}], 'capacities': {'good': 20, 'raw': 20}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'raw': 0, 'good': 6}, 'accepted': ['yield'], 'rejected': [], 'scrap': 3}
    assert request == before

def test_rejected_batch_has_no_scrap():
    request = {'initial': {'raw': 6}, 'recipes': {'yield': {'consume': {'raw': 3}, 'produce': {'good': 2}, 'scrap': 1}}, 'events': [{'id': 'bad', 'revision': 1, 'order': 0, 'recipe': 'yield', 'batches': 2}], 'capacities': {'raw': 6, 'good': 3}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'raw': 6, 'good': 0}, 'accepted': [], 'rejected': ['bad'], 'scrap': 0}
    assert request == before

def test_net_capacity_for_self_consuming_gate():
    request = {'initial': {'wip': 2}, 'recipes': {'rework': {'consume': {'wip': 2}, 'produce': {'wip': 1, 'done': 1}, 'scrap': 0}}, 'events': [{'id': 'rework', 'revision': 1, 'order': 0, 'recipe': 'rework', 'batches': 1}], 'capacities': {'wip': 2, 'done': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'wip': 1, 'done': 1}, 'accepted': ['rework'], 'rejected': [], 'scrap': 0}
    assert request == before

def test_rejected_event_is_not_retried():
    request = {'initial': {'raw': 1}, 'recipes': {'move': {'consume': {'raw': 1}, 'produce': {'wip': 1}, 'scrap': 0}, 'finish': {'consume': {'wip': 1}, 'produce': {'done': 1}, 'scrap': 0}}, 'events': [{'id': 'a_finish', 'revision': 1, 'order': 0, 'recipe': 'finish', 'batches': 1}, {'id': 'b_move', 'revision': 1, 'order': 1, 'recipe': 'move', 'batches': 1}], 'capacities': {'done': 20, 'raw': 20, 'wip': 20}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'raw': 0, 'wip': 1, 'done': 0}, 'accepted': ['b_move'], 'rejected': ['a_finish'], 'scrap': 0}
    assert request == before

def test_recipe_correction_changes_yield_and_dependencies():
    request = {'initial': {'raw': 2}, 'recipes': {'move': {'consume': {'raw': 1}, 'produce': {'wip': 1}, 'scrap': 0}, 'finish': {'consume': {'wip': 1}, 'produce': {'done': 1}, 'scrap': 0}, 'scrap': {'consume': {'raw': 1}, 'produce': {}, 'scrap': 1}}, 'events': [{'id': 'a_move', 'revision': 1, 'order': 0, 'recipe': 'move', 'batches': 2}, {'id': 'a_move', 'revision': 2, 'order': 0, 'recipe': 'scrap', 'batches': 2}, {'id': 'b_finish', 'revision': 1, 'order': 1, 'recipe': 'finish', 'batches': 2}], 'capacities': {'done': 20, 'raw': 20, 'wip': 20}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'raw': 0, 'wip': 0, 'done': 0}, 'accepted': ['a_move'], 'rejected': ['b_finish'], 'scrap': 2}
    assert request == before

def test_partial_join_cannot_borrow_from_missing_branch():
    request = {'initial': {'raw': 2}, 'recipes': {'feed': {'consume': {'raw': 1}, 'produce': {'a': 1}, 'scrap': 0}, 'join': {'consume': {'a': 1, 'b': 1}, 'produce': {'done': 2}, 'scrap': 0}}, 'events': [{'id': 'a_feed', 'revision': 1, 'order': 1, 'recipe': 'feed', 'batches': 1}, {'id': 'b_join', 'revision': 1, 'order': 2, 'recipe': 'join', 'batches': 1}, {'id': 'c_feed', 'revision': 1, 'order': 3, 'recipe': 'feed', 'batches': 1}], 'capacities': {'a': 20, 'b': 20, 'done': 20, 'raw': 20}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'raw': 0, 'a': 2, 'b': 0, 'done': 0}, 'accepted': ['a_feed', 'c_feed'], 'rejected': ['b_join'], 'scrap': 0}
    assert request == before

def test_historical_future_delete():
    request = {'events': [{'id': 'a', 'revision': 1, 'order': 0, 'recipe': 'forward', 'batches': 1}, {'id': 'a', 'revision': 2, 'known_at': 5, 'deleted': True}], 'initial': {'raw': 1}, 'capacities': {'raw': 2, 'mid': 2, 'done': 2}, 'recipes': {'forward': {'consume': {'raw': 1}, 'produce': {'mid': 1}, 'scrap': 0}, 'finish': {'consume': {'mid': 1}, 'produce': {'done': 1}, 'scrap': 0}, 'back': {'consume': {'mid': 1}, 'produce': {'raw': 1}, 'scrap': 0}, 'loss': {'consume': {'raw': 1}, 'produce': {}, 'scrap': 1}}, 'as_of': 4}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'raw': 0, 'mid': 1, 'done': 0}, 'accepted': ['a'], 'rejected': [], 'scrap': 0}
    assert request == before

def test_historical_delete_boundary():
    request = {'events': [{'id': 'a', 'revision': 1, 'order': 0, 'recipe': 'forward', 'batches': 1}, {'id': 'a', 'revision': 2, 'known_at': 5, 'deleted': True}], 'initial': {'raw': 1}, 'capacities': {'raw': 2, 'mid': 2, 'done': 2}, 'recipes': {'forward': {'consume': {'raw': 1}, 'produce': {'mid': 1}, 'scrap': 0}, 'finish': {'consume': {'mid': 1}, 'produce': {'done': 1}, 'scrap': 0}, 'back': {'consume': {'mid': 1}, 'produce': {'raw': 1}, 'scrap': 0}, 'loss': {'consume': {'raw': 1}, 'produce': {}, 'scrap': 1}}, 'as_of': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'raw': 1, 'mid': 0, 'done': 0}, 'accepted': [], 'rejected': [], 'scrap': 0}
    assert request == before

def test_missing_after():
    request = {'events': [{'id': 'a', 'revision': 1, 'order': 0, 'recipe': 'forward', 'batches': 1, 'after': ['missing']}], 'initial': {'raw': 1}, 'capacities': {'raw': 2, 'mid': 2, 'done': 2}, 'recipes': {'forward': {'consume': {'raw': 1}, 'produce': {'mid': 1}, 'scrap': 0}, 'finish': {'consume': {'mid': 1}, 'produce': {'done': 1}, 'scrap': 0}, 'back': {'consume': {'mid': 1}, 'produce': {'raw': 1}, 'scrap': 0}, 'loss': {'consume': {'raw': 1}, 'produce': {}, 'scrap': 1}}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'raw': 1, 'mid': 0, 'done': 0}, 'accepted': [], 'rejected': ['a'], 'scrap': 0}
    assert request == before

def test_dependency_cycle():
    request = {'events': [{'id': 'a', 'revision': 1, 'order': 0, 'recipe': 'forward', 'batches': 1, 'bundle': 'u', 'after': ['b']}, {'id': 'b', 'revision': 1, 'order': 0, 'recipe': 'back', 'batches': 1, 'bundle': 'u', 'after': ['a']}], 'initial': {'raw': 1}, 'capacities': {'raw': 2, 'mid': 2, 'done': 2}, 'recipes': {'forward': {'consume': {'raw': 1}, 'produce': {'mid': 1}, 'scrap': 0}, 'finish': {'consume': {'mid': 1}, 'produce': {'done': 1}, 'scrap': 0}, 'back': {'consume': {'mid': 1}, 'produce': {'raw': 1}, 'scrap': 0}, 'loss': {'consume': {'raw': 1}, 'produce': {}, 'scrap': 1}}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'raw': 1, 'mid': 0, 'done': 0}, 'accepted': [], 'rejected': ['a', 'b'], 'scrap': 0}
    assert request == before

def test_rollback_scrap():
    request = {'events': [{'id': 'a', 'revision': 1, 'order': 0, 'recipe': 'loss', 'batches': 1, 'bundle': 'u'}, {'id': 'b', 'revision': 1, 'order': 0, 'recipe': 'forward', 'batches': 1, 'bundle': 'u'}], 'initial': {'raw': 1}, 'capacities': {'raw': 2, 'mid': 2, 'done': 2}, 'recipes': {'forward': {'consume': {'raw': 1}, 'produce': {'mid': 1}, 'scrap': 0}, 'finish': {'consume': {'mid': 1}, 'produce': {'done': 1}, 'scrap': 0}, 'back': {'consume': {'mid': 1}, 'produce': {'raw': 1}, 'scrap': 0}, 'loss': {'consume': {'raw': 1}, 'produce': {}, 'scrap': 1}}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'raw': 1, 'mid': 0, 'done': 0}, 'accepted': [], 'rejected': ['a', 'b'], 'scrap': 0}
    assert request == before

def test_no_retry_after_supply():
    request = {'events': [{'id': 'a', 'revision': 1, 'order': 0, 'recipe': 'finish', 'batches': 1}, {'id': 'b', 'revision': 1, 'order': 0, 'recipe': 'forward', 'batches': 1}], 'initial': {'raw': 1}, 'capacities': {'raw': 2, 'mid': 2, 'done': 2}, 'recipes': {'forward': {'consume': {'raw': 1}, 'produce': {'mid': 1}, 'scrap': 0}, 'finish': {'consume': {'mid': 1}, 'produce': {'done': 1}, 'scrap': 0}, 'back': {'consume': {'mid': 1}, 'produce': {'raw': 1}, 'scrap': 0}, 'loss': {'consume': {'raw': 1}, 'produce': {}, 'scrap': 1}}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'raw': 0, 'mid': 1, 'done': 0}, 'accepted': ['b'], 'rejected': ['a'], 'scrap': 0}
    assert request == before

def test_search_backtracks_feasible_prefix():
    request = {'events': [{'id': 'a', 'revision': 1, 'order': 0, 'recipe': 'finish', 'batches': 1, 'bundle': 'u'}, {'id': 'b', 'revision': 1, 'order': 0, 'recipe': 'back', 'batches': 1, 'bundle': 'u'}, {'id': 'c', 'revision': 1, 'order': 0, 'recipe': 'forward', 'batches': 1, 'bundle': 'u'}], 'initial': {'mid': 1}, 'capacities': {'raw': 2, 'mid': 2, 'done': 2}, 'recipes': {'forward': {'consume': {'raw': 1}, 'produce': {'mid': 1}, 'scrap': 0}, 'finish': {'consume': {'mid': 1}, 'produce': {'done': 1}, 'scrap': 0}, 'back': {'consume': {'mid': 1}, 'produce': {'raw': 1}, 'scrap': 0}, 'loss': {'consume': {'raw': 1}, 'produce': {}, 'scrap': 1}}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'raw': 0, 'mid': 0, 'done': 1}, 'accepted': ['b', 'c', 'a'], 'rejected': [], 'scrap': 0}
    assert request == before

def test_aggregate_feasible_without_first_step():
    request = {'events': [{'id': 'a', 'revision': 1, 'order': 0, 'recipe': 'forward', 'batches': 1, 'bundle': 'u'}, {'id': 'b', 'revision': 1, 'order': 0, 'recipe': 'back', 'batches': 1, 'bundle': 'u'}], 'initial': {'done': 1}, 'capacities': {'raw': 2, 'mid': 2, 'done': 2}, 'recipes': {'forward': {'consume': {'raw': 1}, 'produce': {'mid': 1}, 'scrap': 0}, 'finish': {'consume': {'mid': 1}, 'produce': {'done': 1}, 'scrap': 0}, 'back': {'consume': {'mid': 1}, 'produce': {'raw': 1}, 'scrap': 0}, 'loss': {'consume': {'raw': 1}, 'produce': {}, 'scrap': 1}}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'raw': 0, 'mid': 0, 'done': 1}, 'accepted': [], 'rejected': ['a', 'b'], 'scrap': 0}
    assert request == before

def test_accepted_external_dependency():
    request = {'events': [{'id': 'a', 'revision': 1, 'order': 0, 'recipe': 'forward', 'batches': 1}, {'id': 'b', 'revision': 1, 'order': 0, 'recipe': 'finish', 'batches': 1, 'after': ['a']}], 'initial': {'raw': 1}, 'capacities': {'raw': 2, 'mid': 2, 'done': 2}, 'recipes': {'forward': {'consume': {'raw': 1}, 'produce': {'mid': 1}, 'scrap': 0}, 'finish': {'consume': {'mid': 1}, 'produce': {'done': 1}, 'scrap': 0}, 'back': {'consume': {'mid': 1}, 'produce': {'raw': 1}, 'scrap': 0}, 'loss': {'consume': {'raw': 1}, 'produce': {}, 'scrap': 1}}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'raw': 0, 'mid': 0, 'done': 1}, 'accepted': ['a', 'b'], 'rejected': [], 'scrap': 0}
    assert request == before

def test_future_bundle_dependency():
    request = {'events': [{'id': 'a', 'revision': 1, 'order': 0, 'recipe': 'forward', 'batches': 1, 'after': ['z']}, {'id': 'z', 'revision': 1, 'order': 0, 'recipe': 'loss', 'batches': 1}], 'initial': {'raw': 1}, 'capacities': {'raw': 2, 'mid': 2, 'done': 2}, 'recipes': {'forward': {'consume': {'raw': 1}, 'produce': {'mid': 1}, 'scrap': 0}, 'finish': {'consume': {'mid': 1}, 'produce': {'done': 1}, 'scrap': 0}, 'back': {'consume': {'mid': 1}, 'produce': {'raw': 1}, 'scrap': 0}, 'loss': {'consume': {'raw': 1}, 'produce': {}, 'scrap': 1}}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'raw': 0, 'mid': 0, 'done': 0}, 'accepted': ['z'], 'rejected': ['a'], 'scrap': 1}
    assert request == before

def test_deleted_member_leaves_rest():
    request = {'events': [{'id': 'a', 'revision': 1, 'order': 0, 'recipe': 'finish', 'batches': 1, 'bundle': 'u'}, {'id': 'z', 'revision': 1, 'order': 0, 'recipe': 'forward', 'batches': 1, 'bundle': 'u'}, {'id': 'a', 'revision': 2, 'deleted': True}], 'initial': {'raw': 1}, 'capacities': {'raw': 2, 'mid': 2, 'done': 2}, 'recipes': {'forward': {'consume': {'raw': 1}, 'produce': {'mid': 1}, 'scrap': 0}, 'finish': {'consume': {'mid': 1}, 'produce': {'done': 1}, 'scrap': 0}, 'back': {'consume': {'mid': 1}, 'produce': {'raw': 1}, 'scrap': 0}, 'loss': {'consume': {'raw': 1}, 'produce': {}, 'scrap': 1}}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'raw': 0, 'mid': 1, 'done': 0}, 'accepted': ['z'], 'rejected': [], 'scrap': 0}
    assert request == before

def test_unit_identity_namespaces():
    request = {'events': [{'id': 'a', 'revision': 1, 'order': 0, 'recipe': 'forward', 'batches': 1, 'bundle': 'b'}, {'id': 'b', 'revision': 1, 'order': 0, 'recipe': 'forward', 'batches': 1}], 'initial': {'raw': 1}, 'capacities': {'raw': 2, 'mid': 2, 'done': 2}, 'recipes': {'forward': {'consume': {'raw': 1}, 'produce': {'mid': 1}, 'scrap': 0}, 'finish': {'consume': {'mid': 1}, 'produce': {'done': 1}, 'scrap': 0}, 'back': {'consume': {'mid': 1}, 'produce': {'raw': 1}, 'scrap': 0}, 'loss': {'consume': {'raw': 1}, 'produce': {}, 'scrap': 1}}}
    before = copy.deepcopy(request)
    assert run(request) == {'inventory': {'raw': 0, 'mid': 1, 'done': 0}, 'accepted': ['a'], 'rejected': ['b'], 'scrap': 0}
    assert request == before

def test_invisible_duplicate_conflict():
    request = {'events': [{'id': 'a', 'revision': 1, 'order': 0, 'recipe': 'forward', 'batches': 1, 'known_at': 9}, {'id': 'a', 'revision': 1, 'order': 0, 'recipe': 'forward', 'batches': 2, 'known_at': 9}], 'initial': {'raw': 1}, 'capacities': {'raw': 2, 'mid': 2, 'done': 2}, 'recipes': {'forward': {'consume': {'raw': 1}, 'produce': {'mid': 1}, 'scrap': 0}, 'finish': {'consume': {'mid': 1}, 'produce': {'done': 1}, 'scrap': 0}, 'back': {'consume': {'mid': 1}, 'produce': {'raw': 1}, 'scrap': 0}, 'loss': {'consume': {'raw': 1}, 'produce': {}, 'scrap': 1}}, 'as_of': 0}
    before = copy.deepcopy(request)
    with pytest.raises(ValueError):
        run(request)
    assert request == before

