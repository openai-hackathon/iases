import copy
import pytest
from fabops.domain import run


def test_zero_calls():
    request = {'attempts': 0, 'max_attempts': 0, 'elapsed': 0, 'deadline': 10}
    before = copy.deepcopy(request)
    assert run(request) == False
    assert request == before

def test_zero_time():
    request = {'attempts': 0, 'max_attempts': 3, 'elapsed': 0, 'deadline': 0}
    before = copy.deepcopy(request)
    assert run(request) == False
    assert request == before

def test_last_attempt():
    request = {'attempts': 2, 'max_attempts': 3, 'elapsed': 9, 'deadline': 10}
    before = copy.deepcopy(request)
    assert run(request) == True
    assert request == before

def test_over_attempts():
    request = {'attempts': 4, 'max_attempts': 3, 'elapsed': 1, 'deadline': 10}
    before = copy.deepcopy(request)
    assert run(request) == False
    assert request == before

def test_over_time():
    request = {'attempts': 1, 'max_attempts': 3, 'elapsed': 11, 'deadline': 10}
    before = copy.deepcopy(request)
    assert run(request) == False
    assert request == before

def test_fractional_time():
    request = {'attempts': 0, 'max_attempts': 1, 'elapsed': 0.5, 'deadline': 1}
    before = copy.deepcopy(request)
    assert run(request) == True
    assert request == before

