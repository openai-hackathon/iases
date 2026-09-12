import copy
import pytest
from fabops.domain import run


def test_empty_filtered():
    request = {'responses': [{'nextSequence': 20, 'observations': []}]}
    before = copy.deepcopy(request)
    assert run(request) == [20]
    assert request == before

def test_one():
    request = {'responses': [{'nextSequence': 2, 'observations': [1]}]}
    before = copy.deepcopy(request)
    assert run(request) == [2]
    assert request == before

def test_resumed():
    request = {'responses': [{'nextSequence': 101, 'observations': [100]}]}
    before = copy.deepcopy(request)
    assert run(request) == [101]
    assert request == before

def test_multiple():
    request = {'responses': [{'nextSequence': 4, 'observations': [1, 2, 3]}, {'nextSequence': 8, 'observations': [4, 7]}]}
    before = copy.deepcopy(request)
    assert run(request) == [4, 8]
    assert request == before

def test_no_observation():
    request = {'responses': [{'nextSequence': 1, 'observations': []}]}
    before = copy.deepcopy(request)
    assert run(request) == [1]
    assert request == before

def test_large():
    request = {'responses': [{'nextSequence': 1000001, 'observations': [1000000]}]}
    before = copy.deepcopy(request)
    assert run(request) == [1000001]
    assert request == before

