import copy
import pytest
from fabops.domain import run


def test_over_order():
    request = {'orders': {'a': 3}, 'receipts': [{'line': 'a', 'quantity': 5}], 'invoices': [{'line': 'a', 'quantity': 4}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [False], 'billed': {'a': 0}}
    assert request == before

def test_partial():
    request = {'orders': {'a': 5}, 'receipts': [{'line': 'a', 'quantity': 5}], 'invoices': [{'line': 'a', 'quantity': 3}, {'line': 'a', 'quantity': 3}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True, False], 'billed': {'a': 3}}
    assert request == before

def test_reversal():
    request = {'orders': {'a': 5}, 'receipts': [{'line': 'a', 'quantity': 5}, {'line': 'a', 'quantity': -3}], 'invoices': [{'line': 'a', 'quantity': 3}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [False], 'billed': {'a': 0}}
    assert request == before

def test_unrelated_receipt():
    request = {'orders': {'a': 5}, 'receipts': [{'line': 'z', 'quantity': 5}], 'invoices': [{'line': 'a', 'quantity': 3}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [False], 'billed': {'a': 0}}
    assert request == before

def test_two_lines():
    request = {'orders': {'a': 5, 'b': 5}, 'receipts': [{'line': 'a', 'quantity': 2}, {'line': 'b', 'quantity': 5}], 'invoices': [{'line': 'a', 'quantity': 3}, {'line': 'b', 'quantity': 5}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [False, True], 'billed': {'a': 0, 'b': 5}}
    assert request == before

def test_exact():
    request = {'orders': {'a': 5}, 'receipts': [{'line': 'a', 'quantity': 2}, {'line': 'a', 'quantity': 3}], 'invoices': [{'line': 'a', 'quantity': 2}, {'line': 'a', 'quantity': 3}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True, True], 'billed': {'a': 5}}
    assert request == before

