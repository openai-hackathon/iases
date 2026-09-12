import copy
import pytest
from fabops.domain import run


def test_correction():
    request = {'rows': [{'group': 'g', 'part': 'p', 'good': False}, {'group': 'g', 'part': 'p', 'good': True}]}
    before = copy.deepcopy(request)
    assert run(request) == {'g': {'good': 1, 'total': 1}}
    assert request == before

def test_move():
    request = {'rows': [{'group': 'g', 'part': 'p', 'good': True}, {'group': 'h', 'part': 'p', 'good': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'h': {'good': 0, 'total': 1}}
    assert request == before

def test_move_back():
    request = {'rows': [{'group': 'g', 'part': 'p', 'good': True}, {'group': 'h', 'part': 'p', 'good': False}, {'group': 'g', 'part': 'p', 'good': True}]}
    before = copy.deepcopy(request)
    assert run(request) == {'g': {'good': 1, 'total': 1}}
    assert request == before

def test_groups():
    request = {'rows': [{'group': 'g', 'part': 'p', 'good': True}, {'group': 'h', 'part': 'q', 'good': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'g': {'good': 1, 'total': 1}, 'h': {'good': 0, 'total': 1}}
    assert request == before

def test_downgrade():
    request = {'rows': [{'group': 'g', 'part': 'p', 'good': True}, {'group': 'g', 'part': 'p', 'good': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'g': {'good': 0, 'total': 1}}
    assert request == before

def test_shared_group():
    request = {'rows': [{'group': 'g', 'part': 'p', 'good': True}, {'group': 'g', 'part': 'q', 'good': True}, {'group': 'h', 'part': 'p', 'good': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'g': {'good': 1, 'total': 1}, 'h': {'good': 0, 'total': 1}}
    assert request == before

