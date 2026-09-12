import copy
import pytest
from fabops.domain import run


def test_replace_oversized():
    request = {'capacity': 4, 'operations': [{'op': 'put', 'key': 'a', 'weight': 2}, {'op': 'put', 'key': 'a', 'weight': 5}]}
    before = copy.deepcopy(request)
    assert run(request) == {'keys': ['a'], 'weight': 2}
    assert request == before

def test_get_promotes():
    request = {'capacity': 4, 'operations': [{'op': 'put', 'key': 'a', 'weight': 2}, {'op': 'put', 'key': 'b', 'weight': 2}, {'op': 'get', 'key': 'a'}, {'op': 'put', 'key': 'c', 'weight': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == {'keys': ['a', 'c'], 'weight': 4}
    assert request == before

def test_replace():
    request = {'capacity': 4, 'operations': [{'op': 'put', 'key': 'a', 'weight': 3}, {'op': 'put', 'key': 'a', 'weight': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == {'keys': ['a'], 'weight': 1}
    assert request == before

def test_missing_get():
    request = {'capacity': 4, 'operations': [{'op': 'put', 'key': 'a', 'weight': 2}, {'op': 'get', 'key': 'z'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'keys': ['a'], 'weight': 2}
    assert request == before

def test_exact():
    request = {'capacity': 4, 'operations': [{'op': 'put', 'key': 'a', 'weight': 2}, {'op': 'put', 'key': 'b', 'weight': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == {'keys': ['a', 'b'], 'weight': 4}
    assert request == before

def test_replace_promotes():
    request = {'capacity': 4, 'operations': [{'op': 'put', 'key': 'a', 'weight': 1}, {'op': 'put', 'key': 'b', 'weight': 2}, {'op': 'put', 'key': 'a', 'weight': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == {'keys': ['b', 'a'], 'weight': 4}
    assert request == before

