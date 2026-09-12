import copy
import pytest
from fabops.domain import run


def test_full_overlap():
    request = {'start': 0, 'end': 6, 'priority': ['safety', 'maintenance'], 'intervals': [{'cause': 'safety', 'start': 0, 'end': 6}, {'cause': 'maintenance', 'start': 0, 'end': 6}]}
    before = copy.deepcopy(request)
    assert run(request) == {'safety': 6, 'maintenance': 0}
    assert request == before

def test_duplicate():
    request = {'start': 0, 'end': 6, 'priority': ['safety', 'maintenance'], 'intervals': [{'cause': 'safety', 'start': 1, 'end': 3}, {'cause': 'safety', 'start': 1, 'end': 3}]}
    before = copy.deepcopy(request)
    assert run(request) == {'safety': 2, 'maintenance': 0}
    assert request == before

def test_clip():
    request = {'start': 0, 'end': 6, 'priority': ['safety', 'maintenance'], 'intervals': [{'cause': 'safety', 'start': -2, 'end': 2}, {'cause': 'maintenance', 'start': 4, 'end': 9}]}
    before = copy.deepcopy(request)
    assert run(request) == {'safety': 2, 'maintenance': 2}
    assert request == before

def test_touching():
    request = {'start': 0, 'end': 6, 'priority': ['safety', 'maintenance'], 'intervals': [{'cause': 'safety', 'start': 0, 'end': 2}, {'cause': 'maintenance', 'start': 2, 'end': 4}]}
    before = copy.deepcopy(request)
    assert run(request) == {'safety': 2, 'maintenance': 2}
    assert request == before

def test_empty_interval():
    request = {'start': 0, 'end': 6, 'priority': ['safety', 'maintenance'], 'intervals': [{'cause': 'safety', 'start': 2, 'end': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == {'safety': 0, 'maintenance': 0}
    assert request == before

def test_nested():
    request = {'start': 0, 'end': 6, 'priority': ['safety', 'maintenance'], 'intervals': [{'cause': 'maintenance', 'start': 0, 'end': 6}, {'cause': 'safety', 'start': 2, 'end': 3}]}
    before = copy.deepcopy(request)
    assert run(request) == {'safety': 1, 'maintenance': 5}
    assert request == before

