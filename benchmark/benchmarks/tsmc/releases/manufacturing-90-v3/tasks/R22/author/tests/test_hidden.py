import copy
import pytest
from fabops.domain import run


def test_wrong_token():
    request = {'commands': [{'op': 'acquire', 'owner': 'a', 'now': 0, 'ttl': 10}, {'op': 'write', 'owner': 'a', 'token': 9, 'now': 1, 'value': 'ok'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, False], 'value': None, 'epoch': 1}
    assert request == before

def test_same_owner_stale():
    request = {'commands': [{'op': 'acquire', 'owner': 'a', 'now': 0, 'ttl': 10}, {'op': 'retire'}, {'op': 'acquire', 'owner': 'a', 'now': 2, 'ttl': 10}, {'op': 'write', 'owner': 'a', 'token': 1, 'now': 3, 'value': 'ok'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, None, 2, False], 'value': None, 'epoch': 2}
    assert request == before

def test_restart_after_retire():
    request = {'commands': [{'op': 'acquire', 'owner': 'a', 'now': 0, 'ttl': 10}, {'op': 'retire'}, {'op': 'restart'}, {'op': 'acquire', 'owner': 'a', 'now': 2, 'ttl': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, None, None, 2], 'value': None, 'epoch': 2}
    assert request == before

def test_new_owner():
    request = {'commands': [{'op': 'acquire', 'owner': 'a', 'now': 0, 'ttl': 10}, {'op': 'acquire', 'owner': 'b', 'now': 10, 'ttl': 10}, {'op': 'write', 'owner': 'a', 'token': 1, 'now': 11, 'value': 'ok'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 2, False], 'value': None, 'epoch': 2}
    assert request == before

def test_expiry():
    request = {'commands': [{'op': 'acquire', 'owner': 'a', 'now': 0, 'ttl': 10}, {'op': 'write', 'owner': 'a', 'token': 1, 'now': 10, 'value': 'ok'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, False], 'value': None, 'epoch': 1}
    assert request == before

def test_restart_value():
    request = {'commands': [{'op': 'acquire', 'owner': 'a', 'now': 0, 'ttl': 10}, {'op': 'write', 'owner': 'a', 'token': 1, 'now': 1, 'value': 'ok'}, {'op': 'restart'}, {'op': 'write', 'owner': 'a', 'token': 9, 'now': 2, 'value': 'bad'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, True, None, False], 'value': 'ok', 'epoch': 1}
    assert request == before

def test_three_epochs():
    request = {'commands': [{'op': 'acquire', 'owner': 'a', 'now': 0, 'ttl': 10}, {'op': 'retire'}, {'op': 'acquire', 'owner': 'a', 'now': 2, 'ttl': 10}, {'op': 'retire'}, {'op': 'acquire', 'owner': 'a', 'now': 4, 'ttl': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, None, 2, None, 3], 'value': None, 'epoch': 3}
    assert request == before

def test_current_token():
    request = {'commands': [{'op': 'acquire', 'owner': 'a', 'now': 0, 'ttl': 10}, {'op': 'retire'}, {'op': 'acquire', 'owner': 'a', 'now': 2, 'ttl': 10}, {'op': 'write', 'owner': 'a', 'token': 2, 'now': 3, 'value': 'ok'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, None, 2, True], 'value': 'ok', 'epoch': 2}
    assert request == before

