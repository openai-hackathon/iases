import copy
import pytest
from fabops.domain import run


def test_retains_deadband():
    request = {'low': 2, 'high': 5, 'initial': False, 'values': [5, 3, 2]}
    before = copy.deepcopy(request)
    assert run(request) == [True, True, False]
    assert request == before

def test_clear_equality():
    request = {'low': 2, 'high': 5, 'initial': True, 'values': [2]}
    before = copy.deepcopy(request)
    assert run(request) == [False]
    assert request == before

def test_reactivate():
    request = {'low': 2, 'high': 5, 'initial': True, 'values': [1, 5]}
    before = copy.deepcopy(request)
    assert run(request) == [False, True]
    assert request == before

def test_negative():
    request = {'low': -5, 'high': -2, 'initial': False, 'values': [-2, -4, -5]}
    before = copy.deepcopy(request)
    assert run(request) == [True, True, False]
    assert request == before

def test_chatter():
    request = {'low': 2, 'high': 5, 'initial': False, 'values': [5, 4, 5, 3]}
    before = copy.deepcopy(request)
    assert run(request) == [True, True, True, True]
    assert request == before

def test_initial_active():
    request = {'low': 2, 'high': 5, 'initial': True, 'values': [3, 4]}
    before = copy.deepcopy(request)
    assert run(request) == [True, True]
    assert request == before

