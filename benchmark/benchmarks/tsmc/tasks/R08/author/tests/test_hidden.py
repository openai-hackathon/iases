import copy
import pytest
from fabops.domain import run


def test_same_key():
    request = {'entries': [{'tenant': 'a', 'key': 'x', 'value': 1}, {'tenant': 'b', 'key': 'x', 'value': 2}], 'queries': [{'tenant': 'a', 'key': 'x'}]}
    before = copy.deepcopy(request)
    assert run(request) == [1]
    assert request == before

def test_case_sensitive():
    request = {'entries': [{'tenant': 'A', 'key': 'x', 'value': 1}, {'tenant': 'a', 'key': 'x', 'value': 2}], 'queries': [{'tenant': 'A', 'key': 'x'}]}
    before = copy.deepcopy(request)
    assert run(request) == [1]
    assert request == before

def test_reverse_collision():
    request = {'entries': [{'tenant': 'a', 'key': 'b:c', 'value': 2}, {'tenant': 'a:b', 'key': 'c', 'value': 1}], 'queries': [{'tenant': 'a', 'key': 'b:c'}]}
    before = copy.deepcopy(request)
    assert run(request) == [2]
    assert request == before

def test_replace():
    request = {'entries': [{'tenant': 'a', 'key': 'x', 'value': 1}, {'tenant': 'a', 'key': 'x', 'value': 3}], 'queries': [{'tenant': 'a', 'key': 'x'}]}
    before = copy.deepcopy(request)
    assert run(request) == [3]
    assert request == before

def test_empty_components():
    request = {'entries': [{'tenant': '', 'key': 'a:b', 'value': 1}, {'tenant': ':a', 'key': 'b', 'value': 2}], 'queries': [{'tenant': '', 'key': 'a:b'}]}
    before = copy.deepcopy(request)
    assert run(request) == [1]
    assert request == before

def test_unicode():
    request = {'entries': [{'tenant': 'factory', 'key': 'sensor-1', 'value': 0}], 'queries': [{'tenant': 'factory', 'key': 'sensor-1'}]}
    before = copy.deepcopy(request)
    assert run(request) == [0]
    assert request == before

