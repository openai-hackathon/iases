import copy
import pytest
from fabops.domain import run


def test_retry_after_reject():
    request = {'stock': {'a': 1, 'b': 0}, 'orders': [{'a': 1, 'b': 1}, {'a': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [False, True], 'stock': {'a': 0, 'b': 0}}
    assert request == before

def test_insufficient():
    request = {'stock': {'a': 1}, 'orders': [{'a': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [False], 'stock': {'a': 1}}
    assert request == before

def test_unknown():
    request = {'stock': {'a': 1}, 'orders': [{'z': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [False], 'stock': {'a': 1}}
    assert request == before

def test_empty_order():
    request = {'stock': {'a': 1}, 'orders': [{}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True], 'stock': {'a': 1}}
    assert request == before

def test_deplete():
    request = {'stock': {'a': 2}, 'orders': [{'a': 1}, {'a': 1}, {'a': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True, True, False], 'stock': {'a': 0}}
    assert request == before

def test_two_items():
    request = {'stock': {'a': 3, 'b': 2}, 'orders': [{'a': 1, 'b': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True], 'stock': {'a': 2, 'b': 0}}
    assert request == before

