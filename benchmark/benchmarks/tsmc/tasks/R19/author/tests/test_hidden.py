import copy
import pytest
from fabops.domain import run


def test_reject_new():
    request = {'events': [{'op': 'start', 'id': 'a'}, {'op': 'shutdown'}, {'op': 'start', 'id': 'b'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': ['a'], 'completed': [], 'active': ['a'], 'state': 'draining'}
    assert request == before

def test_partial():
    request = {'events': [{'op': 'start', 'id': 'a'}, {'op': 'start', 'id': 'b'}, {'op': 'shutdown'}, {'op': 'finish', 'id': 'a'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': ['a', 'b'], 'completed': ['a'], 'active': ['b'], 'state': 'draining'}
    assert request == before

def test_repeat():
    request = {'events': [{'op': 'start', 'id': 'a'}, {'op': 'shutdown'}, {'op': 'shutdown'}, {'op': 'finish', 'id': 'a'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': ['a'], 'completed': ['a'], 'active': [], 'state': 'closed'}
    assert request == before

def test_unknown():
    request = {'events': [{'op': 'finish', 'id': 'x'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [], 'completed': [], 'active': [], 'state': 'open'}
    assert request == before

def test_closed_start():
    request = {'events': [{'op': 'shutdown'}, {'op': 'start', 'id': 'a'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [], 'completed': [], 'active': [], 'state': 'closed'}
    assert request == before

def test_reverse_finish():
    request = {'events': [{'op': 'start', 'id': 'a'}, {'op': 'start', 'id': 'b'}, {'op': 'shutdown'}, {'op': 'finish', 'id': 'b'}, {'op': 'finish', 'id': 'a'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': ['a', 'b'], 'completed': ['b', 'a'], 'active': [], 'state': 'closed'}
    assert request == before

