import copy
import pytest
from fabops.domain import run


def test_blocked():
    request = {'threshold': 2, 'cooldown': 5, 'events': [{'now': 0, 'success': False}, {'now': 1, 'success': False}, {'now': 2, 'success': True}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True, True, False], 'state': 'open', 'failures': 2}
    assert request == before

def test_probe():
    request = {'threshold': 2, 'cooldown': 5, 'events': [{'now': 0, 'success': False}, {'now': 1, 'success': False}, {'now': 6, 'success': True}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True, True, True], 'state': 'closed', 'failures': 0}
    assert request == before

def test_after_probe():
    request = {'threshold': 2, 'cooldown': 5, 'events': [{'now': 0, 'success': False}, {'now': 1, 'success': False}, {'now': 6, 'success': True}, {'now': 7, 'success': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True, True, True, True], 'state': 'closed', 'failures': 1}
    assert request == before

def test_interrupted_streak():
    request = {'threshold': 2, 'cooldown': 5, 'events': [{'now': 0, 'success': False}, {'now': 1, 'success': True}, {'now': 2, 'success': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True, True, True], 'state': 'closed', 'failures': 1}
    assert request == before

def test_failed_probe():
    request = {'threshold': 2, 'cooldown': 5, 'events': [{'now': 0, 'success': False}, {'now': 1, 'success': False}, {'now': 6, 'success': False}, {'now': 7, 'success': True}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True, True, True, False], 'state': 'open', 'failures': 3}
    assert request == before

def test_one_failure():
    request = {'threshold': 2, 'cooldown': 5, 'events': [{'now': 0, 'success': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True], 'state': 'closed', 'failures': 1}
    assert request == before

