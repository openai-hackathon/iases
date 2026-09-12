import copy
import pytest
from fabops.domain import run


def test_zero_ttl():
    request = {'created': 0, 'ttl': 0, 'now': 0, 'value': 1}
    before = copy.deepcopy(request)
    assert run(request) == None
    assert request == before

def test_late_origin():
    request = {'created': 100, 'ttl': 10, 'now': 109, 'value': False}
    before = copy.deepcopy(request)
    assert run(request) == False
    assert request == before

def test_fractional_boundary():
    request = {'created': 2, 'ttl': 0.5, 'now': 2.5, 'value': 7}
    before = copy.deepcopy(request)
    assert run(request) == None
    assert request == before

def test_object():
    request = {'created': 0, 'ttl': 10, 'now': 9, 'value': {'x': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'x': 1}
    assert request == before

def test_negative_origin():
    request = {'created': -4, 'ttl': 2, 'now': -2, 'value': 3}
    before = copy.deepcopy(request)
    assert run(request) == None
    assert request == before

def test_before_boundary():
    request = {'created': 0, 'ttl': 2, 'now': 1, 'value': 0}
    before = copy.deepcopy(request)
    assert run(request) == 0
    assert request == before

