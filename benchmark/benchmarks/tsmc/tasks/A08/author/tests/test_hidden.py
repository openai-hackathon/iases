import copy
import pytest
from fabops.domain import run


def test_all_edges():
    request = {'edges': [0, 10, 20], 'values': [0, 10, 20]}
    before = copy.deepcopy(request)
    assert run(request) == [1, 2]
    assert request == before

def test_single_bin():
    request = {'edges': [0, 1], 'values': [0, 0.5, 1]}
    before = copy.deepcopy(request)
    assert run(request) == [3]
    assert request == before

def test_negative():
    request = {'edges': [-3, -1, 2], 'values': [-3, -1, 2]}
    before = copy.deepcopy(request)
    assert run(request) == [1, 2]
    assert request == before

def test_repeated_max():
    request = {'edges': [0, 5], 'values': [5, 5, 5]}
    before = copy.deepcopy(request)
    assert run(request) == [3]
    assert request == before

def test_uneven_bins():
    request = {'edges': [0, 1, 100], 'values': [0.5, 1, 99, 100]}
    before = copy.deepcopy(request)
    assert run(request) == [1, 3]
    assert request == before

def test_boundary_pair():
    request = {'edges': [2, 4], 'values': [2, 4]}
    before = copy.deepcopy(request)
    assert run(request) == [2]
    assert request == before

