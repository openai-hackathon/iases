import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'commands': []}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [], 'states': [], 'receipts': 0}
    assert request == before

def test_duplicate_after_restart():
    request = {'commands': [{'op': 'execute', 'key': 'k', 'expected': 0, 'value': 1, 'scope': ['fab', 'cell']}, {'op': 'restart'}, {'op': 'execute', 'key': 'k', 'expected': 0, 'value': 1, 'scope': ['fab', 'cell'], 'trace_id': 'new'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'status': 'applied', 'revision': 1, 'value': 1}, {'status': 'restarted'}, {'status': 'applied', 'revision': 1, 'value': 1}], 'states': [[['fab', 'cell'], 1, 1]], 'receipts': 1}
    assert request == before

def test_revision_is_part_of_identity():
    request = {'commands': [{'op': 'execute', 'key': 'k', 'expected': 0, 'value': 1, 'scope': ['fab', 'cell']}, {'op': 'execute', 'key': 'k', 'expected': 1, 'value': 1, 'scope': ['fab', 'cell']}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'status': 'applied', 'revision': 1, 'value': 1}, {'status': 'conflict'}], 'states': [[['fab', 'cell'], 1, 1]], 'receipts': 1}
    assert request == before

def test_changed_value_conflicts():
    request = {'commands': [{'op': 'execute', 'key': 'k', 'expected': 0, 'value': 1, 'scope': ['fab', 'cell']}, {'op': 'execute', 'key': 'k', 'expected': 0, 'value': 2, 'scope': ['fab', 'cell']}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'status': 'applied', 'revision': 1, 'value': 1}, {'status': 'conflict'}], 'states': [[['fab', 'cell'], 1, 1]], 'receipts': 1}
    assert request == before

def test_boolean_not_numeric():
    request = {'commands': [{'op': 'execute', 'key': 'k', 'expected': 0, 'value': True, 'scope': ['fab', 'cell']}, {'op': 'execute', 'key': 'k', 'expected': 0, 'value': 1, 'scope': ['fab', 'cell']}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'status': 'applied', 'revision': 1, 'value': True}, {'status': 'conflict'}], 'states': [[['fab', 'cell'], 1, True]], 'receipts': 1}
    assert request == before

def test_array_order_significant():
    request = {'commands': [{'op': 'execute', 'key': 'k', 'expected': 0, 'value': [1, 2], 'scope': ['fab', 'cell']}, {'op': 'execute', 'key': 'k', 'expected': 0, 'value': [2, 1], 'scope': ['fab', 'cell']}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'status': 'applied', 'revision': 1, 'value': [1, 2]}, {'status': 'conflict'}], 'states': [[['fab', 'cell'], 1, [1, 2]]], 'receipts': 1}
    assert request == before

def test_negative_zero_equivalence():
    request = {'commands': [{'op': 'execute', 'key': 'k', 'expected': 0, 'value': -0.0, 'scope': ['fab', 'cell']}, {'op': 'execute', 'key': 'k', 'expected': 0, 'value': 0, 'scope': ['fab', 'cell']}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'status': 'applied', 'revision': 1, 'value': -0.0}, {'status': 'applied', 'revision': 1, 'value': -0.0}], 'states': [[['fab', 'cell'], 1, -0.0]], 'receipts': 1}
    assert request == before

def test_stale_result_is_cached():
    request = {'commands': [{'op': 'execute', 'key': 'bad', 'expected': 3, 'value': 1, 'scope': ['fab', 'cell']}, {'op': 'execute', 'key': 'good', 'expected': 0, 'value': 2, 'scope': ['fab', 'cell']}, {'op': 'execute', 'key': 'bad', 'expected': 3, 'value': 1, 'scope': ['fab', 'cell']}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'status': 'precondition', 'revision': 0, 'value': None}, {'status': 'applied', 'revision': 1, 'value': 2}, {'status': 'precondition', 'revision': 0, 'value': None}], 'states': [[['fab', 'cell'], 1, 2]], 'receipts': 2}
    assert request == before

def test_rejected_receipt_survives_restart():
    request = {'commands': [{'op': 'execute', 'key': 'k', 'expected': 2, 'value': 1, 'scope': ['fab', 'cell']}, {'op': 'restart'}, {'op': 'execute', 'key': 'k', 'expected': 2, 'value': 1, 'scope': ['fab', 'cell']}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'status': 'precondition', 'revision': 0, 'value': None}, {'status': 'restarted'}, {'status': 'precondition', 'revision': 0, 'value': None}], 'states': [], 'receipts': 1}
    assert request == before

def test_duplicate_reply_not_current_state():
    request = {'commands': [{'op': 'execute', 'key': 'k', 'expected': 0, 'value': 1, 'scope': ['fab', 'cell']}, {'op': 'execute', 'key': 'next', 'expected': 1, 'value': 2, 'scope': ['fab', 'cell']}, {'op': 'execute', 'key': 'k', 'expected': 0, 'value': 1, 'scope': ['fab', 'cell']}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'status': 'applied', 'revision': 1, 'value': 1}, {'status': 'applied', 'revision': 2, 'value': 2}, {'status': 'applied', 'revision': 1, 'value': 1}], 'states': [[['fab', 'cell'], 2, 2]], 'receipts': 2}
    assert request == before

def test_nested_type_boundary():
    request = {'commands': [{'op': 'execute', 'key': 'k', 'expected': 0, 'value': {'x': [False, None]}, 'scope': ['fab', 'cell']}, {'op': 'execute', 'key': 'k', 'expected': 0, 'value': {'x': [0, None]}, 'scope': ['fab', 'cell']}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'status': 'applied', 'revision': 1, 'value': {'x': [False, None]}}, {'status': 'conflict'}], 'states': [[['fab', 'cell'], 1, {'x': [False, None]}]], 'receipts': 1}
    assert request == before

def test_nested_array_permutation():
    request = {'commands': [{'op': 'execute', 'key': 'k', 'expected': 0, 'value': {'x': [{'a': 1}, {'b': 2}]}, 'scope': ['fab', 'cell']}, {'op': 'execute', 'key': 'k', 'expected': 0, 'value': {'x': [{'b': 2}, {'a': 1}]}, 'scope': ['fab', 'cell']}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'status': 'applied', 'revision': 1, 'value': {'x': [{'a': 1}, {'b': 2}]}}, {'status': 'conflict'}], 'states': [[['fab', 'cell'], 1, {'x': [{'a': 1}, {'b': 2}]}]], 'receipts': 1}
    assert request == before

def test_scoped_same_key_after_restart():
    request = {'commands': [{'op': 'execute', 'key': 'k', 'expected': 0, 'value': 1, 'scope': ['a', 'c']}, {'op': 'restart'}, {'op': 'execute', 'key': 'k', 'expected': 0, 'value': 7, 'scope': ['b', 'c']}, {'op': 'execute', 'key': 'k', 'expected': 0, 'value': 1, 'scope': ['a', 'c']}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'status': 'applied', 'revision': 1, 'value': 1}, {'status': 'restarted'}, {'status': 'applied', 'revision': 1, 'value': 7}, {'status': 'applied', 'revision': 1, 'value': 1}], 'states': [[['a', 'c'], 1, 1], [['b', 'c'], 1, 7]], 'receipts': 2}
    assert request == before

def test_crash_restores_existing_state():
    request = {'commands': [{'op': 'execute', 'key': 'k', 'expected': 0, 'value': 1, 'scope': ['fab', 'cell']}, {'op': 'execute', 'key': 'next', 'expected': 1, 'value': 5, 'scope': ['fab', 'cell'], 'crash': True}, {'op': 'restart'}, {'op': 'execute', 'key': 'next', 'expected': 1, 'value': 5, 'scope': ['fab', 'cell']}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'status': 'applied', 'revision': 1, 'value': 1}, {'status': 'crashed'}, {'status': 'restarted'}, {'status': 'applied', 'revision': 2, 'value': 5}], 'states': [[['fab', 'cell'], 2, 5]], 'receipts': 2}
    assert request == before

def test_cached_retry_ignores_crash():
    request = {'commands': [{'op': 'execute', 'key': 'k', 'expected': 0, 'value': 1, 'scope': ['fab', 'cell']}, {'op': 'execute', 'key': 'k', 'expected': 0, 'value': 1, 'scope': ['fab', 'cell'], 'crash': True}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'status': 'applied', 'revision': 1, 'value': 1}, {'status': 'applied', 'revision': 1, 'value': 1}], 'states': [[['fab', 'cell'], 1, 1]], 'receipts': 1}
    assert request == before

def test_numeric_representation_inside_objects():
    request = {'commands': [{'op': 'execute', 'key': 'k', 'expected': 0, 'value': {'z': 1000, 'a': None}, 'scope': ['fab', 'cell']}, {'op': 'execute', 'key': 'k', 'expected': 0, 'value': {'a': None, 'z': 1000.0}, 'scope': ['fab', 'cell']}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'status': 'applied', 'revision': 1, 'value': {'z': 1000, 'a': None}}, {'status': 'applied', 'revision': 1, 'value': {'z': 1000, 'a': None}}], 'states': [[['fab', 'cell'], 1, {'z': 1000, 'a': None}]], 'receipts': 1}
    assert request == before

def test_large_integer_identity_remains_exact():
    request = {'commands': [{'op': 'execute', 'key': 'k', 'expected': 0, 'value': 1234567890123456789012345678901, 'scope': ['fab', 'cell']}, {'op': 'execute', 'key': 'k', 'expected': 0, 'value': 1234567890123456789012345678902, 'scope': ['fab', 'cell']}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'status': 'applied', 'revision': 1, 'value': 1234567890123456789012345678901}, {'status': 'conflict'}], 'states': [[['fab', 'cell'], 1, 1234567890123456789012345678901]], 'receipts': 1}
    assert request == before

def test_integer_exponent_equivalence():
    request = {'commands': [{'op': 'execute', 'key': 'k', 'expected': 0, 'value': 1000000000000000000000000000000, 'scope': ['fab', 'cell']}, {'op': 'execute', 'key': 'k', 'expected': 0, 'value': 1e+30, 'scope': ['fab', 'cell']}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'status': 'applied', 'revision': 1, 'value': 1000000000000000000000000000000}, {'status': 'applied', 'revision': 1, 'value': 1000000000000000000000000000000}], 'states': [[['fab', 'cell'], 1, 1000000000000000000000000000000]], 'receipts': 1}
    assert request == before

