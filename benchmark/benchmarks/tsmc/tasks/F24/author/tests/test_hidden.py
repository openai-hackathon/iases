import copy
import pytest
from fabops.domain import run


def test_valid():
    request = {'roles': ['qa', 'eng'], 'events': [{'op': 'edit', 'revision': 1}, {'op': 'approve', 'revision': 1, 'role': 'qa'}, {'op': 'approve', 'revision': 1, 'role': 'eng'}, {'op': 'activate'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'activations': [True], 'active': 1}
    assert request == before

def test_stale_approval():
    request = {'roles': ['qa', 'eng'], 'events': [{'op': 'edit', 'revision': 2}, {'op': 'approve', 'revision': 1, 'role': 'qa'}, {'op': 'approve', 'revision': 2, 'role': 'eng'}, {'op': 'activate'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'activations': [False], 'active': None}
    assert request == before

def test_revoke():
    request = {'roles': ['qa', 'eng'], 'events': [{'op': 'edit', 'revision': 1}, {'op': 'approve', 'revision': 1, 'role': 'qa'}, {'op': 'approve', 'revision': 1, 'role': 'eng'}, {'op': 'revoke', 'role': 'qa'}, {'op': 'activate'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'activations': [False], 'active': None}
    assert request == before

def test_retain_active():
    request = {'roles': ['qa', 'eng'], 'events': [{'op': 'edit', 'revision': 1}, {'op': 'approve', 'revision': 1, 'role': 'qa'}, {'op': 'approve', 'revision': 1, 'role': 'eng'}, {'op': 'activate'}, {'op': 'edit', 'revision': 2}, {'op': 'activate'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'activations': [True, False], 'active': 1}
    assert request == before

def test_foreign_role():
    request = {'roles': ['qa', 'eng'], 'events': [{'op': 'edit', 'revision': 1}, {'op': 'approve', 'revision': 1, 'role': 'ops'}, {'op': 'activate'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'activations': [False], 'active': None}
    assert request == before

def test_revision_zero():
    request = {'roles': ['qa', 'eng'], 'events': [{'op': 'edit', 'revision': 0}, {'op': 'approve', 'revision': 0, 'role': 'qa'}, {'op': 'approve', 'revision': 0, 'role': 'eng'}, {'op': 'activate'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'activations': [True], 'active': 0}
    assert request == before

