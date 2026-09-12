import copy
import pytest
from fabops.domain import run


def test_midnight_start():
    request = {'start': 0, 'end': 60, 'minutes': [0, 59, 60]}
    before = copy.deepcopy(request)
    assert run(request) == [True, True, False]
    assert request == before

def test_midnight_end():
    request = {'start': 1380, 'end': 0, 'minutes': [0, 1379, 1380, 1439]}
    before = copy.deepcopy(request)
    assert run(request) == [False, False, True, True]
    assert request == before

def test_short_wrap():
    request = {'start': 1439, 'end': 1, 'minutes': [1439, 0, 1]}
    before = copy.deepcopy(request)
    assert run(request) == [True, True, False]
    assert request == before

def test_equal_nonzero():
    request = {'start': 20, 'end': 20, 'minutes': [19, 20, 21]}
    before = copy.deepcopy(request)
    assert run(request) == [False, False, False]
    assert request == before

def test_single_minute():
    request = {'start': 4, 'end': 5, 'minutes': [3, 4, 5]}
    before = copy.deepcopy(request)
    assert run(request) == [False, True, False]
    assert request == before

def test_wrap_middle():
    request = {'start': 1200, 'end': 300, 'minutes': [1201, 200, 400]}
    before = copy.deepcopy(request)
    assert run(request) == [True, True, False]
    assert request == before

