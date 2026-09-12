import copy
import pytest
from fabops.domain import run


def test_reverse():
    request = {'gap': 2, 'times': [4, 2, 0]}
    before = copy.deepcopy(request)
    assert run(request) == [[0, 4, 3]]
    assert request == before

def test_exact_gap():
    request = {'gap': 2, 'times': [0, 2]}
    before = copy.deepcopy(request)
    assert run(request) == [[0, 2, 2]]
    assert request == before

def test_duplicates():
    request = {'gap': 2, 'times': [0, 0, 2]}
    before = copy.deepcopy(request)
    assert run(request) == [[0, 2, 2]]
    assert request == before

def test_zero_gap():
    request = {'gap': 0, 'times': [1, 1, 2]}
    before = copy.deepcopy(request)
    assert run(request) == [[1, 1, 1], [2, 2, 1]]
    assert request == before

def test_two_sessions():
    request = {'gap': 2, 'times': [9, 1, 0, 8]}
    before = copy.deepcopy(request)
    assert run(request) == [[0, 1, 2], [8, 9, 2]]
    assert request == before

def test_negative():
    request = {'gap': 2, 'times': [0, -2, -4]}
    before = copy.deepcopy(request)
    assert run(request) == [[-4, 0, 3]]
    assert request == before

