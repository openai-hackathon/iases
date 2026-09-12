import copy
import pytest
from fabops.domain import run


def test_partial():
    request = {'ids': ['a', 'b'], 'responses': [{'id': 'b', 'value': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == [None, 2]
    assert request == before

def test_unrelated():
    request = {'ids': ['a'], 'responses': [{'id': 'z', 'value': 9}]}
    before = copy.deepcopy(request)
    assert run(request) == [None]
    assert request == before

def test_zero():
    request = {'ids': ['a'], 'responses': [{'id': 'a', 'value': 0}]}
    before = copy.deepcopy(request)
    assert run(request) == [0]
    assert request == before

def test_false():
    request = {'ids': ['a'], 'responses': [{'id': 'a', 'value': False}]}
    before = copy.deepcopy(request)
    assert run(request) == [False]
    assert request == before

def test_request_order():
    request = {'ids': ['b', 'a'], 'responses': [{'id': 'a', 'value': 1}, {'id': 'b', 'value': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == [2, 1]
    assert request == before

def test_null():
    request = {'ids': ['a', 'b'], 'responses': [{'id': 'b', 'value': None}, {'id': 'a', 'value': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == [1, None]
    assert request == before

