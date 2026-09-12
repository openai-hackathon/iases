import copy
import pytest
from fabops.domain import run


def test_after_charge():
    request = {'stock': 5, 'balance': 10, 'orders': [{'quantity': 2, 'price': 3, 'failure': 'after_charge'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [False], 'stock': 5, 'balance': 10}
    assert request == before

def test_retry():
    request = {'stock': 2, 'balance': 3, 'orders': [{'quantity': 2, 'price': 3, 'failure': 'charge'}, {'quantity': 2, 'price': 3, 'failure': 'none'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [False, True], 'stock': 0, 'balance': 0}
    assert request == before

def test_no_balance():
    request = {'stock': 5, 'balance': 1, 'orders': [{'quantity': 2, 'price': 3, 'failure': 'none'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [False], 'stock': 5, 'balance': 1}
    assert request == before

def test_free_order():
    request = {'stock': 2, 'balance': 0, 'orders': [{'quantity': 1, 'price': 0, 'failure': 'none'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True], 'stock': 1, 'balance': 0}
    assert request == before

def test_two_failures():
    request = {'stock': 5, 'balance': 10, 'orders': [{'quantity': 2, 'price': 3, 'failure': 'charge'}, {'quantity': 2, 'price': 3, 'failure': 'after_charge'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [False, False], 'stock': 5, 'balance': 10}
    assert request == before

def test_success_then_fail():
    request = {'stock': 5, 'balance': 10, 'orders': [{'quantity': 2, 'price': 3, 'failure': 'none'}, {'quantity': 1, 'price': 2, 'failure': 'after_charge'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True, False], 'stock': 3, 'balance': 7}
    assert request == before

