import copy
import pytest
from fabops.domain import run


def test_max():
    request = {'timeouts': [300]}
    before = copy.deepcopy(request)
    assert run(request) == [True]
    assert request == before

def test_zero():
    request = {'timeouts': [0]}
    before = copy.deepcopy(request)
    assert run(request) == [False]
    assert request == before

def test_float():
    request = {'timeouts': [1.0]}
    before = copy.deepcopy(request)
    assert run(request) == [False]
    assert request == before

def test_min():
    request = {'timeouts': [1]}
    before = copy.deepcopy(request)
    assert run(request) == [True]
    assert request == before

def test_mixed():
    request = {'timeouts': [30, True, False]}
    before = copy.deepcopy(request)
    assert run(request) == [True, False, False]
    assert request == before

def test_over():
    request = {'timeouts': [301]}
    before = copy.deepcopy(request)
    assert run(request) == [False]
    assert request == before

