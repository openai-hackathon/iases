import copy
import pytest
from fabops.domain import run


def test_duplicate():
    request = {'start': 0, 'end': 10, 'maintenance': [[2, 6], [2, 6]]}
    before = copy.deepcopy(request)
    assert run(request) == 6
    assert request == before

def test_nested():
    request = {'start': 0, 'end': 10, 'maintenance': [[1, 9], [3, 5]]}
    before = copy.deepcopy(request)
    assert run(request) == 2
    assert request == before

def test_clip():
    request = {'start': 3, 'end': 8, 'maintenance': [[0, 4], [7, 10]]}
    before = copy.deepcopy(request)
    assert run(request) == 3
    assert request == before

def test_outside():
    request = {'start': 3, 'end': 8, 'maintenance': [[0, 2], [9, 10]]}
    before = copy.deepcopy(request)
    assert run(request) == 5
    assert request == before

def test_zero():
    request = {'start': 4, 'end': 4, 'maintenance': [[0, 8]]}
    before = copy.deepcopy(request)
    assert run(request) == 0
    assert request == before

def test_unsorted():
    request = {'start': 0, 'end': 10, 'maintenance': [[6, 8], [1, 3], [2, 7]]}
    before = copy.deepcopy(request)
    assert run(request) == 3
    assert request == before

