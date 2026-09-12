import copy
import pytest
from fabops.domain import run


def test_inclusive():
    request = {'readings': [[0, 4]], 'queries': [2], 'tolerance': 2}
    before = copy.deepcopy(request)
    assert run(request) == [4]
    assert request == before

def test_tie():
    request = {'readings': [[4, 8], [0, 2]], 'queries': [2], 'tolerance': 2}
    before = copy.deepcopy(request)
    assert run(request) == [2]
    assert request == before

def test_zero_value():
    request = {'readings': [[0, 0]], 'queries': [0], 'tolerance': 0}
    before = copy.deepcopy(request)
    assert run(request) == [0]
    assert request == before

def test_ordered_output():
    request = {'readings': [[0, 2], [4, 8]], 'queries': [4, 0], 'tolerance': 0}
    before = copy.deepcopy(request)
    assert run(request) == [8, 2]
    assert request == before

def test_negative():
    request = {'readings': [[-4, 2]], 'queries': [0], 'tolerance': 1}
    before = copy.deepcopy(request)
    assert run(request) == [None]
    assert request == before

def test_nearest():
    request = {'readings': [[0, 2], [3, 6], [9, 18]], 'queries': [2], 'tolerance': 2}
    before = copy.deepcopy(request)
    assert run(request) == [6]
    assert request == before

