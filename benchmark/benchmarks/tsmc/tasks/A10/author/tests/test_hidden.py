import copy
import pytest
from fabops.domain import run


def test_negative_tie():
    request = {'values': ['-1.005']}
    before = copy.deepcopy(request)
    assert run(request) == '-1.01'
    assert request == before

def test_offsetting():
    request = {'values': ['1.234', '-0.234']}
    before = copy.deepcopy(request)
    assert run(request) == '1.00'
    assert request == before

def test_many_small():
    request = {'values': ['0.003', '0.003', '0.003', '0.003']}
    before = copy.deepcopy(request)
    assert run(request) == '0.01'
    assert request == before

def test_double_tie():
    request = {'values': ['0.005', '0.005']}
    before = copy.deepcopy(request)
    assert run(request) == '0.01'
    assert request == before

def test_exact_cents():
    request = {'values': ['1.25', '2.75']}
    before = copy.deepcopy(request)
    assert run(request) == '4.00'
    assert request == before

def test_negative_sum():
    request = {'values': ['-0.004', '-0.004']}
    before = copy.deepcopy(request)
    assert run(request) == '-0.01'
    assert request == before

