import copy
import pytest
from fabops.domain import run


def test_merge():
    request = {'stock': {'a': 1, 'b': 3}, 'operations': [{'inputs': ['a', 'b'], 'outputs': {'c': 4}}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True], 'stock': {'c': 4}}
    assert request == before

def test_reuse():
    request = {'stock': {'a': 4}, 'operations': [{'inputs': ['a'], 'outputs': {'b': 4}}, {'inputs': ['a'], 'outputs': {'c': 4}}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True, False], 'stock': {'b': 4}}
    assert request == before

def test_collision():
    request = {'stock': {'a': 2, 'b': 2}, 'operations': [{'inputs': ['a'], 'outputs': {'b': 2}}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [False], 'stock': {'a': 2, 'b': 2}}
    assert request == before

def test_zero_output():
    request = {'stock': {'a': 4}, 'operations': [{'inputs': ['a'], 'outputs': {'b': 4, 'c': 0}}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [False], 'stock': {'a': 4}}
    assert request == before

def test_small_loss():
    request = {'stock': {'a': 2, 'b': 3}, 'operations': [{'inputs': ['a', 'b'], 'outputs': {'c': 4}}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [False], 'stock': {'a': 2, 'b': 3}}
    assert request == before

def test_chain():
    request = {'stock': {'a': 4}, 'operations': [{'inputs': ['a'], 'outputs': {'b': 4}}, {'inputs': ['b'], 'outputs': {'c': 4}}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True, True], 'stock': {'c': 4}}
    assert request == before

