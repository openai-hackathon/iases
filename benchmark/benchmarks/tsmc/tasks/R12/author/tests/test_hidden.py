import copy
import pytest
from fabops.domain import run


def test_two_poison():
    request = {'messages': [{'id': '0', 'valid': False}, {'id': '1', 'valid': False}], 'max_attempts': 3}
    before = copy.deepcopy(request)
    assert run(request) == {'processed': [], 'dead_letter': ['0', '1'], 'attempts': {'0': 3, '1': 3}}
    assert request == before

def test_middle():
    request = {'messages': [{'id': '0', 'valid': True}, {'id': '1', 'valid': False}, {'id': '2', 'valid': True}], 'max_attempts': 2}
    before = copy.deepcopy(request)
    assert run(request) == {'processed': ['0', '2'], 'dead_letter': ['1'], 'attempts': {'0': 1, '1': 2, '2': 1}}
    assert request == before

def test_one_attempt():
    request = {'messages': [{'id': '0', 'valid': False}, {'id': '1', 'valid': True}], 'max_attempts': 1}
    before = copy.deepcopy(request)
    assert run(request) == {'processed': ['1'], 'dead_letter': ['0'], 'attempts': {'0': 1, '1': 1}}
    assert request == before

def test_all_good():
    request = {'messages': [{'id': '0', 'valid': True}, {'id': '1', 'valid': True}], 'max_attempts': 3}
    before = copy.deepcopy(request)
    assert run(request) == {'processed': ['0', '1'], 'dead_letter': [], 'attempts': {'0': 1, '1': 1}}
    assert request == before

def test_last():
    request = {'messages': [{'id': '0', 'valid': True}, {'id': '1', 'valid': False}], 'max_attempts': 4}
    before = copy.deepcopy(request)
    assert run(request) == {'processed': ['0'], 'dead_letter': ['1'], 'attempts': {'0': 1, '1': 4}}
    assert request == before

def test_alternating():
    request = {'messages': [{'id': '0', 'valid': False}, {'id': '1', 'valid': True}, {'id': '2', 'valid': False}], 'max_attempts': 2}
    before = copy.deepcopy(request)
    assert run(request) == {'processed': ['1'], 'dead_letter': ['0', '2'], 'attempts': {'0': 2, '1': 1, '2': 2}}
    assert request == before

