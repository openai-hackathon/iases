import copy
import pytest
from fabops.domain import run


def test_cancel_head():
    request = {'capacity': 3, 'operations': [{'op': 'enqueue', 'id': 'a', 'weight': 2}, {'op': 'enqueue', 'id': 'b', 'weight': 2}, {'op': 'enqueue', 'id': 'c', 'weight': 1}, {'op': 'cancel', 'id': 'b'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'admitted': ['a', 'c'], 'active': ['a', 'c'], 'pending': []}
    assert request == before

def test_fifo():
    request = {'capacity': 3, 'operations': [{'op': 'enqueue', 'id': 'a', 'weight': 2}, {'op': 'enqueue', 'id': 'b', 'weight': 2}, {'op': 'enqueue', 'id': 'c', 'weight': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == {'admitted': ['a'], 'active': ['a'], 'pending': ['b', 'c']}
    assert request == before

def test_drain():
    request = {'capacity': 3, 'operations': [{'op': 'enqueue', 'id': 'a', 'weight': 3}, {'op': 'enqueue', 'id': 'b', 'weight': 2}, {'op': 'enqueue', 'id': 'c', 'weight': 1}, {'op': 'release', 'id': 'a'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'admitted': ['a', 'b', 'c'], 'active': ['b', 'c'], 'pending': []}
    assert request == before

def test_unknown():
    request = {'capacity': 3, 'operations': [{'op': 'cancel', 'id': 'x'}, {'op': 'release', 'id': 'x'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'admitted': [], 'active': [], 'pending': []}
    assert request == before

def test_cancel_tail():
    request = {'capacity': 3, 'operations': [{'op': 'enqueue', 'id': 'a', 'weight': 3}, {'op': 'enqueue', 'id': 'b', 'weight': 2}, {'op': 'enqueue', 'id': 'c', 'weight': 1}, {'op': 'cancel', 'id': 'c'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'admitted': ['a'], 'active': ['a'], 'pending': ['b']}
    assert request == before

def test_cancel_active():
    request = {'capacity': 3, 'operations': [{'op': 'enqueue', 'id': 'a', 'weight': 1}, {'op': 'cancel', 'id': 'a'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'admitted': ['a'], 'active': ['a'], 'pending': []}
    assert request == before

