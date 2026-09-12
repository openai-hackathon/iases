import copy
import pytest
from fabops.domain import run


def test_nested():
    request = {'commands': [{'key': 'k', 'method': 'POST', 'target': '/lot', 'payload': {'x': {'a': 1, 'b': 2}}, 'result': 'a'}, {'key': 'k', 'method': 'POST', 'target': '/lot', 'payload': {'x': {'b': 2, 'a': 1}}, 'result': 'b'}]}
    before = copy.deepcopy(request)
    assert run(request) == ['a', 'a']
    assert request == before

def test_target():
    request = {'commands': [{'key': 'k', 'method': 'POST', 'target': '/a', 'payload': {}, 'result': 'a'}, {'key': 'k', 'method': 'POST', 'target': '/b', 'payload': {}, 'result': 'b'}]}
    before = copy.deepcopy(request)
    assert run(request) == ['a', 'conflict']
    assert request == before

def test_method():
    request = {'commands': [{'key': 'k', 'method': 'POST', 'target': '/a', 'payload': {}, 'result': 'a'}, {'key': 'k', 'method': 'PUT', 'target': '/a', 'payload': {}, 'result': 'b'}]}
    before = copy.deepcopy(request)
    assert run(request) == ['a', 'conflict']
    assert request == before

def test_list_order():
    request = {'commands': [{'key': 'k', 'method': 'POST', 'target': '/a', 'payload': [1, 2], 'result': 'a'}, {'key': 'k', 'method': 'POST', 'target': '/a', 'payload': [2, 1], 'result': 'b'}]}
    before = copy.deepcopy(request)
    assert run(request) == ['a', 'conflict']
    assert request == before

def test_separate_keys():
    request = {'commands': [{'key': 'k', 'method': 'POST', 'target': '/a', 'payload': {}, 'result': 'a'}, {'key': 'j', 'method': 'POST', 'target': '/a', 'payload': {}, 'result': 'b'}]}
    before = copy.deepcopy(request)
    assert run(request) == ['a', 'b']
    assert request == before

def test_conflict_keeps_original():
    request = {'commands': [{'key': 'k', 'method': 'POST', 'target': '/a', 'payload': 1, 'result': 'a'}, {'key': 'k', 'method': 'POST', 'target': '/a', 'payload': 2, 'result': 'b'}, {'key': 'k', 'method': 'POST', 'target': '/a', 'payload': 1, 'result': 'c'}]}
    before = copy.deepcopy(request)
    assert run(request) == ['a', 'conflict', 'a']
    assert request == before

