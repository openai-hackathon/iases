import copy
import pytest
from fabops.domain import run


def test_chain():
    request = {'start': 'a', 'end': 'c', 'edges': [['a', 'b', 2], ['b', 'c', 3]]}
    before = copy.deepcopy(request)
    assert run(request) == 5
    assert request == before

def test_asymmetric():
    request = {'start': 'b', 'end': 'a', 'edges': [['a', 'b', 1], ['b', 'a', 9]]}
    before = copy.deepcopy(request)
    assert run(request) == 9
    assert request == before

def test_detour():
    request = {'start': 'a', 'end': 'c', 'edges': [['a', 'c', 9], ['a', 'b', 2], ['b', 'c', 1]]}
    before = copy.deepcopy(request)
    assert run(request) == 3
    assert request == before

def test_cycle():
    request = {'start': 'c', 'end': 'a', 'edges': [['a', 'b', 1], ['b', 'c', 1]]}
    before = copy.deepcopy(request)
    assert run(request) == None
    assert request == before

def test_zero_edge():
    request = {'start': 'a', 'end': 'b', 'edges': [['a', 'b', 0]]}
    before = copy.deepcopy(request)
    assert run(request) == 0
    assert request == before

def test_parallel():
    request = {'start': 'a', 'end': 'b', 'edges': [['a', 'b', 8], ['a', 'b', 3]]}
    before = copy.deepcopy(request)
    assert run(request) == 3
    assert request == before

