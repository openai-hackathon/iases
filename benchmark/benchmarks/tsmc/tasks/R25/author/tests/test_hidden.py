import copy
import pytest
from fabops.domain import run


def test_retry():
    request = {'values': [1], 'fail': True, 'retry': True}
    before = copy.deepcopy(request)
    assert run(request) == {'columns': ['value', 'unit'], 'rows': [[1, 'Pa']]}
    assert request == before

def test_empty_rollback():
    request = {'values': [], 'fail': True, 'retry': False}
    before = copy.deepcopy(request)
    assert run(request) == {'columns': ['value'], 'rows': []}
    assert request == before

def test_empty_retry():
    request = {'values': [], 'fail': True, 'retry': True}
    before = copy.deepcopy(request)
    assert run(request) == {'columns': ['value', 'unit'], 'rows': []}
    assert request == before

def test_preserve_order():
    request = {'values': [3, 1, 2], 'fail': True, 'retry': True}
    before = copy.deepcopy(request)
    assert run(request) == {'columns': ['value', 'unit'], 'rows': [[3, 'Pa'], [1, 'Pa'], [2, 'Pa']]}
    assert request == before

def test_duplicates():
    request = {'values': [1, 1], 'fail': False, 'retry': True}
    before = copy.deepcopy(request)
    assert run(request) == {'columns': ['value', 'unit'], 'rows': [[1, 'Pa'], [1, 'Pa']]}
    assert request == before

def test_negative():
    request = {'values': [-1, 0], 'fail': True, 'retry': False}
    before = copy.deepcopy(request)
    assert run(request) == {'columns': ['value'], 'rows': [[-1], [0]]}
    assert request == before

