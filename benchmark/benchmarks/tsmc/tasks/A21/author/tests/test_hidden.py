import copy
import pytest
from fabops.domain import run


def test_tie_sort():
    request = {'rows': [{'time': 1, 'id': 'b', 'value': 'b'}, {'time': 1, 'id': 'a', 'value': 'a'}], 'cursor': None, 'limit': 1}
    before = copy.deepcopy(request)
    assert run(request) == {'rows': [{'time': 1, 'id': 'a', 'value': 'a'}], 'next_cursor': [1, 'a']}
    assert request == before

def test_exclusive():
    request = {'rows': [{'time': 1, 'id': 'a', 'value': 'a'}], 'cursor': [1, 'a'], 'limit': 2}
    before = copy.deepcopy(request)
    assert run(request) == {'rows': [], 'next_cursor': [1, 'a']}
    assert request == before

def test_limit():
    request = {'rows': [{'time': 1, 'id': 'a', 'value': 'a'}, {'time': 1, 'id': 'b', 'value': 'b'}, {'time': 1, 'id': 'c', 'value': 'c'}], 'cursor': [1, 'a'], 'limit': 1}
    before = copy.deepcopy(request)
    assert run(request) == {'rows': [{'time': 1, 'id': 'b', 'value': 'b'}], 'next_cursor': [1, 'b']}
    assert request == before

def test_missing_cursor():
    request = {'rows': [{'time': 1, 'id': 'c', 'value': 'c'}], 'cursor': [1, 'b'], 'limit': 2}
    before = copy.deepcopy(request)
    assert run(request) == {'rows': [{'time': 1, 'id': 'c', 'value': 'c'}], 'next_cursor': [1, 'c']}
    assert request == before

def test_unsorted():
    request = {'rows': [{'time': 2, 'id': 'a', 'value': 'a'}, {'time': 1, 'id': 'c', 'value': 'c'}, {'time': 1, 'id': 'a', 'value': 'a'}], 'cursor': [1, 'b'], 'limit': 2}
    before = copy.deepcopy(request)
    assert run(request) == {'rows': [{'time': 1, 'id': 'c', 'value': 'c'}, {'time': 2, 'id': 'a', 'value': 'a'}], 'next_cursor': [2, 'a']}
    assert request == before

def test_beyond():
    request = {'rows': [{'time': 1, 'id': 'a', 'value': 'a'}], 'cursor': [2, 'z'], 'limit': 2}
    before = copy.deepcopy(request)
    assert run(request) == {'rows': [], 'next_cursor': [2, 'z']}
    assert request == before

