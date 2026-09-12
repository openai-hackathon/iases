import copy
import pytest
from fabops.domain import run


def test_zero_boundary():
    request = {'now': 0, 'lots': [{'expires_at': 0}]}
    before = copy.deepcopy(request)
    assert run(request) == [False]
    assert request == before

def test_historical():
    request = {'now': -3, 'lots': [{'expires_at': -4}, {'expires_at': -3}, {'expires_at': -2}]}
    before = copy.deepcopy(request)
    assert run(request) == [False, False, True]
    assert request == before

def test_mixed():
    request = {'now': 20, 'lots': [{'expires_at': 19}, {'expires_at': 20}, {'expires_at': 21}, {'expires_at': 40}]}
    before = copy.deepcopy(request)
    assert run(request) == [False, False, True, True]
    assert request == before

def test_large_epoch():
    request = {'now': 1000000, 'lots': [{'expires_at': 1000000}, {'expires_at': 1000001}]}
    before = copy.deepcopy(request)
    assert run(request) == [False, True]
    assert request == before

def test_duplicates():
    request = {'now': 4, 'lots': [{'expires_at': 4}, {'expires_at': 4}, {'expires_at': 5}]}
    before = copy.deepcopy(request)
    assert run(request) == [False, False, True]
    assert request == before

def test_far_future():
    request = {'now': 0, 'lots': [{'expires_at': 100}]}
    before = copy.deepcopy(request)
    assert run(request) == [True]
    assert request == before

