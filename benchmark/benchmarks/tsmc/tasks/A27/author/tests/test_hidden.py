import copy
import pytest
from fabops.domain import run


def test_reverse():
    request = {'changes': [{'effective': 5, 'value': 'c'}, {'effective': 1, 'value': 'a'}]}
    before = copy.deepcopy(request)
    assert run(request) == [{'start': 1, 'end': 5, 'value': 'a'}, {'start': 5, 'end': None, 'value': 'c'}]
    assert request == before

def test_correction():
    request = {'changes': [{'effective': 1, 'value': 'a'}, {'effective': 1, 'value': 'b'}]}
    before = copy.deepcopy(request)
    assert run(request) == [{'start': 1, 'end': None, 'value': 'b'}]
    assert request == before

def test_same_value():
    request = {'changes': [{'effective': 1, 'value': 'a'}, {'effective': 3, 'value': 'a'}]}
    before = copy.deepcopy(request)
    assert run(request) == [{'start': 1, 'end': 3, 'value': 'a'}, {'start': 3, 'end': None, 'value': 'a'}]
    assert request == before

def test_negative():
    request = {'changes': [{'effective': 0, 'value': 'b'}, {'effective': -2, 'value': 'a'}]}
    before = copy.deepcopy(request)
    assert run(request) == [{'start': -2, 'end': 0, 'value': 'a'}, {'start': 0, 'end': None, 'value': 'b'}]
    assert request == before

def test_middle_correction():
    request = {'changes': [{'effective': 1, 'value': 'a'}, {'effective': 3, 'value': 'b'}, {'effective': 5, 'value': 'c'}, {'effective': 3, 'value': 'd'}]}
    before = copy.deepcopy(request)
    assert run(request) == [{'start': 1, 'end': 3, 'value': 'a'}, {'start': 3, 'end': 5, 'value': 'd'}, {'start': 5, 'end': None, 'value': 'c'}]
    assert request == before

def test_late_before():
    request = {'changes': [{'effective': 5, 'value': 'b'}, {'effective': 2, 'value': 'a'}]}
    before = copy.deepcopy(request)
    assert run(request) == [{'start': 2, 'end': 5, 'value': 'a'}, {'start': 5, 'end': None, 'value': 'b'}]
    assert request == before

