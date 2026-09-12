import copy
import pytest
from fabops.domain import run


def test_translate_after():
    request = {'points': [[1, 2]], 'turns': 1, 'dx': 4, 'dy': 5}
    before = copy.deepcopy(request)
    assert run(request) == [[2, 6]]
    assert request == before

def test_negative():
    request = {'points': [[1, 2]], 'turns': -1, 'dx': 0, 'dy': 0}
    before = copy.deepcopy(request)
    assert run(request) == [[2, -1]]
    assert request == before

def test_three():
    request = {'points': [[1, 2]], 'turns': 3, 'dx': 0, 'dy': 0}
    before = copy.deepcopy(request)
    assert run(request) == [[2, -1]]
    assert request == before

def test_wrap():
    request = {'points': [[1, 2]], 'turns': 5, 'dx': 0, 'dy': 0}
    before = copy.deepcopy(request)
    assert run(request) == [[-2, 1]]
    assert request == before

def test_origin():
    request = {'points': [[0, 0]], 'turns': 3, 'dx': -1, 'dy': 2}
    before = copy.deepcopy(request)
    assert run(request) == [[-1, 2]]
    assert request == before

def test_many():
    request = {'points': [[1, 0], [0, 1]], 'turns': 1, 'dx': 1, 'dy': 1}
    before = copy.deepcopy(request)
    assert run(request) == [[1, 2], [0, 1]]
    assert request == before

