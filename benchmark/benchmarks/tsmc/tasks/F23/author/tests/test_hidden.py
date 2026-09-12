import copy
import pytest
from fabops.domain import run


def test_shared_resource():
    request = {'jobs': [{'id': 'a', 'resource': 'm', 'duration': 3, 'depends': [], 'release': 0}, {'id': 'b', 'resource': 'm', 'duration': 2, 'depends': [], 'release': 0}]}
    before = copy.deepcopy(request)
    assert run(request) == {'a': [0, 3], 'b': [3, 5]}
    assert request == before

def test_release():
    request = {'jobs': [{'id': 'a', 'resource': 'm', 'duration': 3, 'depends': [], 'release': 5}]}
    before = copy.deepcopy(request)
    assert run(request) == {'a': [5, 8]}
    assert request == before

def test_reverse():
    request = {'jobs': [{'id': 'b', 'resource': 'n', 'duration': 2, 'depends': ['a'], 'release': 0}, {'id': 'a', 'resource': 'm', 'duration': 3, 'depends': [], 'release': 0}]}
    before = copy.deepcopy(request)
    assert run(request) == {'a': [0, 3], 'b': [3, 5]}
    assert request == before

def test_fan_in():
    request = {'jobs': [{'id': 'a', 'resource': 'm', 'duration': 3, 'depends': [], 'release': 0}, {'id': 'b', 'resource': 'n', 'duration': 5, 'depends': [], 'release': 0}, {'id': 'c', 'resource': 'q', 'duration': 1, 'depends': ['a', 'b'], 'release': 0}]}
    before = copy.deepcopy(request)
    assert run(request) == {'a': [0, 3], 'b': [0, 5], 'c': [5, 6]}
    assert request == before

def test_zero_duration():
    request = {'jobs': [{'id': 'a', 'resource': 'm', 'duration': 0, 'depends': [], 'release': 4}, {'id': 'b', 'resource': 'n', 'duration': 2, 'depends': ['a'], 'release': 0}]}
    before = copy.deepcopy(request)
    assert run(request) == {'a': [4, 4], 'b': [4, 6]}
    assert request == before

def test_later_release():
    request = {'jobs': [{'id': 'a', 'resource': 'm', 'duration': 3, 'depends': [], 'release': 0}, {'id': 'b', 'resource': 'n', 'duration': 2, 'depends': ['a'], 'release': 8}]}
    before = copy.deepcopy(request)
    assert run(request) == {'a': [0, 3], 'b': [8, 10]}
    assert request == before

def test_cyclic_graph():
    request = {'jobs': [{'id': 'a', 'resource': 'm', 'duration': 1, 'release': 0, 'depends': ['b']}, {'id': 'b', 'resource': 'n', 'duration': 1, 'release': 0, 'depends': ['a']}]}
    before = copy.deepcopy(request)
    with pytest.raises(ValueError):
        run(request)
    assert request == before

