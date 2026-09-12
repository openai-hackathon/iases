import copy
import pytest
from fabops.domain import run


def test_partial():
    request = {'required': ['door', 'vacuum'], 'observations': {'door': True}}
    before = copy.deepcopy(request)
    assert run(request) == False
    assert request == before

def test_one_unsafe():
    request = {'required': ['door', 'vacuum'], 'observations': {'door': True, 'vacuum': False}}
    before = copy.deepcopy(request)
    assert run(request) == False
    assert request == before

def test_numeric_true():
    request = {'required': ['door'], 'observations': {'door': 1}}
    before = copy.deepcopy(request)
    assert run(request) == False
    assert request == before

def test_text_true():
    request = {'required': ['door'], 'observations': {'door': 'true'}}
    before = copy.deepcopy(request)
    assert run(request) == False
    assert request == before

def test_unrelated():
    request = {'required': ['door'], 'observations': {'vacuum': True}}
    before = copy.deepcopy(request)
    assert run(request) == False
    assert request == before

def test_all_safe():
    request = {'required': ['door', 'vacuum'], 'observations': {'door': True, 'vacuum': True}}
    before = copy.deepcopy(request)
    assert run(request) == True
    assert request == before

