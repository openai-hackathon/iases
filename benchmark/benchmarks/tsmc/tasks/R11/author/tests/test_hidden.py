import copy
import pytest
from fabops.domain import run


def test_past():
    request = {'header': 'Tue, 31 Dec 2024 23:59:59 GMT', 'now': 'Wed, 01 Jan 2025 00:00:00 GMT'}
    before = copy.deepcopy(request)
    assert run(request) == 0
    assert request == before

def test_boundary():
    request = {'header': 'Wed, 01 Jan 2025 00:00:00 GMT', 'now': 'Wed, 01 Jan 2025 00:00:00 GMT'}
    before = copy.deepcopy(request)
    assert run(request) == 0
    assert request == before

def test_day():
    request = {'header': 'Thu, 02 Jan 2025 00:00:00 GMT', 'now': 'Wed, 01 Jan 2025 00:00:00 GMT'}
    before = copy.deepcopy(request)
    assert run(request) == 86400
    assert request == before

def test_whitespace():
    request = {'header': ' 120 ', 'now': 'Wed, 01 Jan 2025 00:00:00 GMT'}
    before = copy.deepcopy(request)
    assert run(request) == 120
    assert request == before

def test_negative():
    request = {'header': '-1', 'now': 'Wed, 01 Jan 2025 00:00:00 GMT'}
    before = copy.deepcopy(request)
    assert run(request) == None
    assert request == before

def test_fractional():
    request = {'header': '1.5', 'now': 'Wed, 01 Jan 2025 00:00:00 GMT'}
    before = copy.deepcopy(request)
    assert run(request) == None
    assert request == before

