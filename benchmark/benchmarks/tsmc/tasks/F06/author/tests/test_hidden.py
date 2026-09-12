import copy
import pytest
from fabops.domain import run


def test_minor_numeric():
    request = {'versions': ['1.9.0', '1.12.0']}
    before = copy.deepcopy(request)
    assert run(request) == '1.12.0'
    assert request == before

def test_patch_numeric():
    request = {'versions': ['1.1.9', '1.1.11']}
    before = copy.deepcopy(request)
    assert run(request) == '1.1.11'
    assert request == before

def test_major_priority():
    request = {'versions': ['2.0.0', '1.99.99']}
    before = copy.deepcopy(request)
    assert run(request) == '2.0.0'
    assert request == before

def test_patch_tie_break():
    request = {'versions': ['1.2.1', '1.2.2']}
    before = copy.deepcopy(request)
    assert run(request) == '1.2.2'
    assert request == before

def test_duplicate():
    request = {'versions': ['1.0.0', '1.0.0']}
    before = copy.deepcopy(request)
    assert run(request) == '1.0.0'
    assert request == before

def test_zero():
    request = {'versions': ['0.0.0', '0.0.12', '0.0.9']}
    before = copy.deepcopy(request)
    assert run(request) == '0.0.12'
    assert request == before

