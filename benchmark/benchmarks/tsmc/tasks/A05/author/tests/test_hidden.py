import copy
import pytest
from fabops.domain import run


def test_large_bad_lot():
    request = {'lots': [{'good': 1, 'tested': 1}, {'good': 0, 'tested': 7}]}
    before = copy.deepcopy(request)
    assert run(request) == 0.125
    assert request == before

def test_reversed():
    request = {'lots': [{'good': 0, 'tested': 3}, {'good': 1, 'tested': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == 0.25
    assert request == before

def test_all_good():
    request = {'lots': [{'good': 2, 'tested': 2}, {'good': 6, 'tested': 6}]}
    before = copy.deepcopy(request)
    assert run(request) == 1.0
    assert request == before

def test_all_bad():
    request = {'lots': [{'good': 0, 'tested': 2}, {'good': 0, 'tested': 6}]}
    before = copy.deepcopy(request)
    assert run(request) == 0.0
    assert request == before

def test_three_lots():
    request = {'lots': [{'good': 2, 'tested': 2}, {'good': 1, 'tested': 2}, {'good': 1, 'tested': 4}]}
    before = copy.deepcopy(request)
    assert run(request) == 0.5
    assert request == before

def test_duplicate_lots():
    request = {'lots': [{'good': 1, 'tested': 1}, {'good': 0, 'tested': 3}, {'good': 1, 'tested': 1}, {'good': 0, 'tested': 3}]}
    before = copy.deepcopy(request)
    assert run(request) == 0.25
    assert request == before

