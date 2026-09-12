import copy
import pytest
from fabops.domain import run


def test_maximum():
    request = {'values': [2, 1], 'q': 1}
    before = copy.deepcopy(request)
    assert run(request) == 2
    assert request == before

def test_upper_quartile():
    request = {'values': [1, 2, 3, 4], 'q': 0.75}
    before = copy.deepcopy(request)
    assert run(request) == 3
    assert request == before

def test_odd_median():
    request = {'values': [3, 1, 2], 'q': 0.5}
    before = copy.deepcopy(request)
    assert run(request) == 2
    assert request == before

def test_noninteger_rank():
    request = {'values': [1, 2, 3, 4], 'q': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == 3
    assert request == before

def test_duplicates():
    request = {'values': [1, 1, 1, 9], 'q': 0.75}
    before = copy.deepcopy(request)
    assert run(request) == 1
    assert request == before

def test_negative():
    request = {'values': [-1, -4, -2, -3], 'q': 0.5}
    before = copy.deepcopy(request)
    assert run(request) == -3
    assert request == before

