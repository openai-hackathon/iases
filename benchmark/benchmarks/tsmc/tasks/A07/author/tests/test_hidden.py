import copy
import pytest
from fabops.domain import run


def test_all_missing():
    request = {'values': [None, None]}
    before = copy.deepcopy(request)
    assert run(request) == None
    assert request == before

def test_negative():
    request = {'values': [-4, 2]}
    before = copy.deepcopy(request)
    assert run(request) == -1.0
    assert request == before

def test_mixed():
    request = {'values': [None, -2, 0, 2]}
    before = copy.deepcopy(request)
    assert run(request) == 0.0
    assert request == before

def test_repeated_missing():
    request = {'values': [None, 8, None]}
    before = copy.deepcopy(request)
    assert run(request) == 8.0
    assert request == before

def test_single_zero():
    request = {'values': [0]}
    before = copy.deepcopy(request)
    assert run(request) == 0.0
    assert request == before

def test_four_values():
    request = {'values': [2, 4, 6, 8, None]}
    before = copy.deepcopy(request)
    assert run(request) == 5.0
    assert request == before

