import copy
import pytest
from fabops.domain import run


def test_lower_spike():
    request = {'baseline': [0, 2], 'k': 2, 'measurements': [-100]}
    before = copy.deepcopy(request)
    assert run(request) == [True]
    assert request == before

def test_sample_denominator():
    request = {'baseline': [0, 2], 'k': 1, 'measurements': [2.25]}
    before = copy.deepcopy(request)
    assert run(request) == [False]
    assert request == before

def test_zero_width():
    request = {'baseline': [1, 1], 'k': 1, 'measurements': [1, 2]}
    before = copy.deepcopy(request)
    assert run(request) == [False, True]
    assert request == before

def test_zero_multiplier():
    request = {'baseline': [0, 2], 'k': 0, 'measurements': [1, 2]}
    before = copy.deepcopy(request)
    assert run(request) == [False, True]
    assert request == before

def test_opposite_outliers():
    request = {'baseline': [0, 2], 'k': 2, 'measurements': [-100, 100]}
    before = copy.deepcopy(request)
    assert run(request) == [True, True]
    assert request == before

def test_constant_baseline():
    request = {'baseline': [4, 4, 4], 'k': 1, 'measurements': [3, 4, 5]}
    before = copy.deepcopy(request)
    assert run(request) == [True, False, True]
    assert request == before

