import copy
import pytest
from fabops.domain import run


def test_reverse():
    request = {'labels': [1, -1]}
    before = copy.deepcopy(request)
    assert run(request) == [True, False]
    assert request == before

def test_all_pass():
    request = {'labels': [-1, -1]}
    before = copy.deepcopy(request)
    assert run(request) == [False, False]
    assert request == before

def test_all_fail():
    request = {'labels': [1, 1]}
    before = copy.deepcopy(request)
    assert run(request) == [True, True]
    assert request == before

def test_rare_fail():
    request = {'labels': [-1, -1, 1, -1]}
    before = copy.deepcopy(request)
    assert run(request) == [False, False, True, False]
    assert request == before

def test_alternating():
    request = {'labels': [1, -1, 1]}
    before = copy.deepcopy(request)
    assert run(request) == [True, False, True]
    assert request == before

def test_last_fail():
    request = {'labels': [-1, -1, -1, 1]}
    before = copy.deepcopy(request)
    assert run(request) == [False, False, False, True]
    assert request == before

