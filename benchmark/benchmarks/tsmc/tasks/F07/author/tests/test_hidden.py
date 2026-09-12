import copy
import pytest
from fabops.domain import run


def test_repeat_at_end():
    request = {'route': ['a', 'b', 'a'], 'completed': 3}
    before = copy.deepcopy(request)
    assert run(request) == None
    assert request == before

def test_triple_repeat():
    request = {'route': ['a', 'a', 'a', 'b'], 'completed': 3}
    before = copy.deepcopy(request)
    assert run(request) == 'b'
    assert request == before

def test_done():
    request = {'route': ['a', 'b'], 'completed': 2}
    before = copy.deepcopy(request)
    assert run(request) == None
    assert request == before

def test_same_names():
    request = {'route': ['a', 'a'], 'completed': 2}
    before = copy.deepcopy(request)
    assert run(request) == None
    assert request == before

def test_middle():
    request = {'route': ['a', 'b', 'c'], 'completed': 2}
    before = copy.deepcopy(request)
    assert run(request) == 'c'
    assert request == before

def test_later_repeat():
    request = {'route': ['a', 'b', 'c', 'b', 'd'], 'completed': 4}
    before = copy.deepcopy(request)
    assert run(request) == 'd'
    assert request == before

