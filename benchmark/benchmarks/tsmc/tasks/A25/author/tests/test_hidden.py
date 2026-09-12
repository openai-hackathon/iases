import copy
import pytest
from fabops.domain import run


def test_cycle():
    request = {'seeds': ['a'], 'edges': [['a', 'b'], ['b', 'c'], ['c', 'a']]}
    before = copy.deepcopy(request)
    assert run(request) == ['b', 'c']
    assert request == before

def test_diamond():
    request = {'seeds': ['a'], 'edges': [['a', 'b'], ['a', 'c'], ['b', 'd'], ['c', 'd']]}
    before = copy.deepcopy(request)
    assert run(request) == ['b', 'c', 'd']
    assert request == before

def test_multiple_seeds():
    request = {'seeds': ['a', 'b'], 'edges': [['a', 'b'], ['b', 'c']]}
    before = copy.deepcopy(request)
    assert run(request) == ['c']
    assert request == before

def test_self():
    request = {'seeds': ['a'], 'edges': [['a', 'a']]}
    before = copy.deepcopy(request)
    assert run(request) == []
    assert request == before

def test_duplicate():
    request = {'seeds': ['a'], 'edges': [['a', 'b'], ['a', 'b']]}
    before = copy.deepcopy(request)
    assert run(request) == ['b']
    assert request == before

def test_branch():
    request = {'seeds': ['a'], 'edges': [['a', 'b'], ['b', 'd'], ['x', 'z']]}
    before = copy.deepcopy(request)
    assert run(request) == ['b', 'd']
    assert request == before

