import copy
import pytest
from fabops.domain import run


def test_reset_on_pass():
    request = {'route': ['a', 'b'], 'max_retries': 1, 'events': [False, True]}
    before = copy.deepcopy(request)
    assert run(request) == {'state': 'active', 'step': 'b', 'retries': 0}
    assert request == before

def test_empty():
    request = {'route': [], 'max_retries': 1, 'events': []}
    before = copy.deepcopy(request)
    assert run(request) == {'state': 'done', 'step': None, 'retries': 0}
    assert request == before

def test_no_retry():
    request = {'route': ['a'], 'max_retries': 0, 'events': [False]}
    before = copy.deepcopy(request)
    assert run(request) == {'state': 'scrap', 'step': None, 'retries': 1}
    assert request == before

def test_extra_events():
    request = {'route': ['a'], 'max_retries': 1, 'events': [True, False]}
    before = copy.deepcopy(request)
    assert run(request) == {'state': 'done', 'step': None, 'retries': 0}
    assert request == before

def test_two_allowed():
    request = {'route': ['a'], 'max_retries': 2, 'events': [False, False]}
    before = copy.deepcopy(request)
    assert run(request) == {'state': 'active', 'step': 'a', 'retries': 2}
    assert request == before

def test_repeat_rework():
    request = {'route': ['a', 'b'], 'max_retries': 1, 'events': [False, True, False, True]}
    before = copy.deepcopy(request)
    assert run(request) == {'state': 'done', 'step': None, 'retries': 0}
    assert request == before

