import copy
import pytest
from fabops.domain import run


def test_jitter_crosses_cap():
    request = {'base': 1, 'cap': 10, 'attempt': 3, 'jitter': 5}
    before = copy.deepcopy(request)
    assert run(request) == 10
    assert request == before

def test_exponential():
    request = {'base': 1, 'cap': 100, 'attempt': 3, 'jitter': 0}
    before = copy.deepcopy(request)
    assert run(request) == 8
    assert request == before

def test_fractional():
    request = {'base': 0.5, 'cap': 5, 'attempt': 2, 'jitter': 0.5}
    before = copy.deepcopy(request)
    assert run(request) == 2.5
    assert request == before

def test_minimum_cap():
    request = {'base': 2, 'cap': 2, 'attempt': 0, 'jitter': 3}
    before = copy.deepcopy(request)
    assert run(request) == 2
    assert request == before

def test_large_attempt():
    request = {'base': 1, 'cap': 100, 'attempt': 20, 'jitter': 1}
    before = copy.deepcopy(request)
    assert run(request) == 100
    assert request == before

def test_within_cap():
    request = {'base': 2, 'cap': 30, 'attempt': 2, 'jitter': 3}
    before = copy.deepcopy(request)
    assert run(request) == 11
    assert request == before

