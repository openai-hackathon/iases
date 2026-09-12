import copy
import pytest
from fabops.domain import run


def test_replay_after_delete():
    request = {'records': [{'key': 'a', 'version': 2, 'value': None, 'deleted': True}, {'key': 'a', 'version': 1, 'value': 2, 'deleted': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {}
    assert request == before

def test_old_update():
    request = {'records': [{'key': 'a', 'version': 2, 'value': 3, 'deleted': False}, {'key': 'a', 'version': 1, 'value': 2, 'deleted': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'a': 3}
    assert request == before

def test_zero():
    request = {'records': [{'key': 'a', 'version': 1, 'value': 0, 'deleted': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'a': 0}
    assert request == before

def test_restore():
    request = {'records': [{'key': 'a', 'version': 2, 'value': None, 'deleted': True}, {'key': 'a', 'version': 3, 'value': 4, 'deleted': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'a': 4}
    assert request == before

def test_other_key():
    request = {'records': [{'key': 'a', 'version': 1, 'value': 2, 'deleted': False}, {'key': 'b', 'version': 2, 'value': None, 'deleted': True}]}
    before = copy.deepcopy(request)
    assert run(request) == {'a': 2}
    assert request == before

def test_old_delete():
    request = {'records': [{'key': 'a', 'version': 3, 'value': 4, 'deleted': False}, {'key': 'a', 'version': 2, 'value': None, 'deleted': True}]}
    before = copy.deepcopy(request)
    assert run(request) == {'a': 4}
    assert request == before

