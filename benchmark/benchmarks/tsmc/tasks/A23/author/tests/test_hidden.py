import copy
import pytest
from fabops.domain import run


def test_weighted():
    request = {'summaries': [{'count': 1, 'mean': 0, 'm2': 0}, {'count': 3, 'mean': 4, 'm2': 0}]}
    before = copy.deepcopy(request)
    assert run(request) == {'count': 4, 'mean': 3.0, 'variance': 3.0}
    assert request == before

def test_reverse_weighted():
    request = {'summaries': [{'count': 3, 'mean': 4, 'm2': 0}, {'count': 1, 'mean': 0, 'm2': 0}]}
    before = copy.deepcopy(request)
    assert run(request) == {'count': 4, 'mean': 3.0, 'variance': 3.0}
    assert request == before

def test_zero_group():
    request = {'summaries': [{'count': 0, 'mean': 100, 'm2': 0}, {'count': 2, 'mean': 2, 'm2': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == {'count': 2, 'mean': 2.0, 'variance': 1.0}
    assert request == before

def test_negative():
    request = {'summaries': [{'count': 1, 'mean': -2, 'm2': 0}, {'count': 1, 'mean': 2, 'm2': 0}]}
    before = copy.deepcopy(request)
    assert run(request) == {'count': 2, 'mean': 0.0, 'variance': 4.0}
    assert request == before

def test_within_between():
    request = {'summaries': [{'count': 2, 'mean': 0, 'm2': 2}, {'count': 2, 'mean': 4, 'm2': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == {'count': 4, 'mean': 2.0, 'variance': 5.0}
    assert request == before

def test_all_empty():
    request = {'summaries': [{'count': 0, 'mean': 0, 'm2': 0}]}
    before = copy.deepcopy(request)
    assert run(request) == {'count': 0, 'mean': None, 'variance': None}
    assert request == before

