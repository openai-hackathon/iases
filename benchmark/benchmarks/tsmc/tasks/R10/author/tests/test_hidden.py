import copy
import pytest
from fabops.domain import run


def test_no_first():
    request = {'cursor': 0, 'acks': [2, 3]}
    before = copy.deepcopy(request)
    assert run(request) == 0
    assert request == before

def test_resume():
    request = {'cursor': 5, 'acks': [8, 6]}
    before = copy.deepcopy(request)
    assert run(request) == 6
    assert request == before

def test_unordered():
    request = {'cursor': 3, 'acks': [6, 4, 5]}
    before = copy.deepcopy(request)
    assert run(request) == 6
    assert request == before

def test_old():
    request = {'cursor': 5, 'acks': [1, 2]}
    before = copy.deepcopy(request)
    assert run(request) == 5
    assert request == before

def test_fills_gap():
    request = {'cursor': 5, 'acks': [7, 8, 6, 6]}
    before = copy.deepcopy(request)
    assert run(request) == 8
    assert request == before

def test_far_ahead():
    request = {'cursor': 10, 'acks': [100]}
    before = copy.deepcopy(request)
    assert run(request) == 10
    assert request == before

