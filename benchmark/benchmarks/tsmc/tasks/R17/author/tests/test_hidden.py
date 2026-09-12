import copy
import pytest
from fabops.domain import run


def test_many_checks():
    request = {'capacity': 1, 'rate': 1, 'times': [0, 250, 500, 750, 1000]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True, False, False, False, True], 'milli_tokens': 0}
    assert request == before

def test_cap():
    request = {'capacity': 1, 'rate': 1, 'times': [10000]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True], 'milli_tokens': 0}
    assert request == before

def test_twice_rate():
    request = {'capacity': 1, 'rate': 2, 'times': [0, 250, 500]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True, False, True], 'milli_tokens': 0}
    assert request == before

def test_burst():
    request = {'capacity': 2, 'rate': 1, 'times': [0, 0, 0]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True, True, False], 'milli_tokens': 0}
    assert request == before

def test_partial_after_success():
    request = {'capacity': 2, 'rate': 1, 'times': [0, 500]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True, True], 'milli_tokens': 500}
    assert request == before

def test_same_time():
    request = {'capacity': 1, 'rate': 1, 'times': [0, 0]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True, False], 'milli_tokens': 0}
    assert request == before

