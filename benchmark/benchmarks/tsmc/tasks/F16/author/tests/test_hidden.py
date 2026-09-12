import copy
import pytest
from fabops.domain import run


def test_expiry():
    request = {'at': '2025-01-01T02:00+00:00', 'qualifications': [{'id': 'q', 'start': '2025-01-01T00:00+00:00', 'end': '2025-01-01T02:00+00:00'}]}
    before = copy.deepcopy(request)
    assert run(request) == []
    assert request == before

def test_previous_day():
    request = {'at': '2024-12-31T20:00-05:00', 'qualifications': [{'id': 'q', 'start': '2025-01-01T00:00+00:00', 'end': '2025-01-01T02:00+00:00'}]}
    before = copy.deepcopy(request)
    assert run(request) == ['q']
    assert request == before

def test_window_offset():
    request = {'at': '2025-01-01T01:00+00:00', 'qualifications': [{'id': 'q', 'start': '2025-01-01T08:00+08:00', 'end': '2025-01-01T10:00+08:00'}]}
    before = copy.deepcopy(request)
    assert run(request) == ['q']
    assert request == before

def test_same_wall():
    request = {'at': '2025-01-01T01:00+08:00', 'qualifications': [{'id': 'q', 'start': '2025-01-01T00:00+00:00', 'end': '2025-01-01T02:00+00:00'}]}
    before = copy.deepcopy(request)
    assert run(request) == []
    assert request == before

def test_offset_expiry():
    request = {'at': '2025-01-01T10:00+08:00', 'qualifications': [{'id': 'q', 'start': '2025-01-01T00:00+00:00', 'end': '2025-01-01T02:00+00:00'}]}
    before = copy.deepcopy(request)
    assert run(request) == []
    assert request == before

def test_zero_window():
    request = {'at': '2025-01-01T00:00+00:00', 'qualifications': [{'id': 'q', 'start': '2025-01-01T00:00+00:00', 'end': '2025-01-01T00:00+00:00'}]}
    before = copy.deepcopy(request)
    assert run(request) == []
    assert request == before

