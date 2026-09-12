import copy
import pytest
from fabops.domain import run


def test_half_bar():
    request = {'measurements': [{'unit': 'bar', 'value': 0.5}]}
    before = copy.deepcopy(request)
    assert run(request) == [50000]
    assert request == before

def test_negative():
    request = {'measurements': [{'unit': 'kPa', 'value': -1}]}
    before = copy.deepcopy(request)
    assert run(request) == [-1000]
    assert request == before

def test_zero():
    request = {'measurements': [{'unit': 'bar', 'value': 0}]}
    before = copy.deepcopy(request)
    assert run(request) == [0]
    assert request == before

def test_mixed():
    request = {'measurements': [{'unit': 'bar', 'value': 1}, {'unit': 'Pa', 'value': 1}, {'unit': 'kPa', 'value': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == [100000, 1, 1000]
    assert request == before

def test_negative_bar():
    request = {'measurements': [{'unit': 'bar', 'value': -2}]}
    before = copy.deepcopy(request)
    assert run(request) == [-200000]
    assert request == before

def test_fractional():
    request = {'measurements': [{'unit': 'kPa', 'value': 0.25}]}
    before = copy.deepcopy(request)
    assert run(request) == [250]
    assert request == before

