import copy
import pytest
from fabops.domain import run


def test_one_field():
    request = {'product': 'p', 'machine': 'm', 'rules': [{'id': 'a', 'product': 'p', 'machine': '*', 'revision': 1}, {'id': 'b', 'product': '*', 'machine': '*', 'revision': 9}]}
    before = copy.deepcopy(request)
    assert run(request) == 'a'
    assert request == before

def test_revision():
    request = {'product': 'p', 'machine': 'm', 'rules': [{'id': 'a', 'product': 'p', 'machine': 'm', 'revision': 1}, {'id': 'b', 'product': 'p', 'machine': 'm', 'revision': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == 'b'
    assert request == before

def test_id_tie():
    request = {'product': 'p', 'machine': 'm', 'rules': [{'id': 'b', 'product': 'p', 'machine': 'm', 'revision': 2}, {'id': 'a', 'product': 'p', 'machine': 'm', 'revision': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == 'a'
    assert request == before

def test_machine_specific():
    request = {'product': 'p', 'machine': 'm', 'rules': [{'id': 'a', 'product': '*', 'machine': 'm', 'revision': 1}, {'id': 'b', 'product': '*', 'machine': '*', 'revision': 8}]}
    before = copy.deepcopy(request)
    assert run(request) == 'a'
    assert request == before

def test_specific_zero():
    request = {'product': 'p', 'machine': 'm', 'rules': [{'id': 'a', 'product': 'p', 'machine': 'm', 'revision': 0}, {'id': 'b', 'product': 'p', 'machine': '*', 'revision': 4}]}
    before = copy.deepcopy(request)
    assert run(request) == 'a'
    assert request == before

def test_fallback():
    request = {'product': 'p', 'machine': 'm', 'rules': [{'id': 'a', 'product': 'q', 'machine': 'm', 'revision': 8}, {'id': 'b', 'product': '*', 'machine': '*', 'revision': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == 'b'
    assert request == before

