import copy
import pytest
from fabops.domain import run


def test_multiple():
    request = {'samples': [[1, 8], [2, 1], [3, 3], [4, 2]]}
    before = copy.deepcopy(request)
    assert run(request) == 5
    assert request == before

def test_unordered():
    request = {'samples': [[3, 3], [1, 8], [2, 1]]}
    before = copy.deepcopy(request)
    assert run(request) == 3
    assert request == before

def test_zero_reset():
    request = {'samples': [[1, 9], [2, 0], [3, 2]]}
    before = copy.deepcopy(request)
    assert run(request) == 2
    assert request == before

def test_equal():
    request = {'samples': [[1, 4], [2, 4]]}
    before = copy.deepcopy(request)
    assert run(request) == 0
    assert request == before

def test_initial_zero():
    request = {'samples': [[1, 0], [2, 7]]}
    before = copy.deepcopy(request)
    assert run(request) == 7
    assert request == before

def test_reset_then_increase():
    request = {'samples': [[1, 100], [2, 4], [3, 9]]}
    before = copy.deepcopy(request)
    assert run(request) == 9
    assert request == before

