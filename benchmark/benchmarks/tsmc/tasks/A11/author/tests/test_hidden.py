import copy
import pytest
from fabops.domain import run


def test_triangle():
    request = {'samples': [[0, 0], [2, 4], [4, 0]]}
    before = copy.deepcopy(request)
    assert run(request) == 8
    assert request == before

def test_irregular():
    request = {'samples': [[0, 0], [1, 4], [4, 4]]}
    before = copy.deepcopy(request)
    assert run(request) == 14
    assert request == before

def test_unordered():
    request = {'samples': [[4, 0], [0, 0], [2, 4]]}
    before = copy.deepcopy(request)
    assert run(request) == 8
    assert request == before

def test_decline():
    request = {'samples': [[0, 8], [2, 0]]}
    before = copy.deepcopy(request)
    assert run(request) == 8
    assert request == before

def test_offset():
    request = {'samples': [[10, 2], [13, 4]]}
    before = copy.deepcopy(request)
    assert run(request) == 9
    assert request == before

def test_all_zero():
    request = {'samples': [[0, 0], [7, 0]]}
    before = copy.deepcopy(request)
    assert run(request) == 0
    assert request == before

