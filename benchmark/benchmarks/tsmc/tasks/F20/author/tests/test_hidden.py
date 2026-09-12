import copy
import pytest
from fabops.domain import run


def test_net():
    request = {'events': [{'type': 'receipt', 'quantity': 5}, {'type': 'reversal', 'quantity': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == 3
    assert request == before

def test_cancel():
    request = {'events': [{'type': 'receipt', 'quantity': 5}, {'type': 'reversal', 'quantity': 5}]}
    before = copy.deepcopy(request)
    assert run(request) == 0
    assert request == before

def test_multiple():
    request = {'events': [{'type': 'receipt', 'quantity': 2}, {'type': 'receipt', 'quantity': 3}, {'type': 'reversal', 'quantity': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == 4
    assert request == before

def test_all_reversed():
    request = {'events': [{'type': 'reversal', 'quantity': 1}, {'type': 'reversal', 'quantity': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == -3
    assert request == before

def test_zero_reversal():
    request = {'events': [{'type': 'reversal', 'quantity': 0}]}
    before = copy.deepcopy(request)
    assert run(request) == 0
    assert request == before

def test_later_receipt():
    request = {'events': [{'type': 'reversal', 'quantity': 5}, {'type': 'receipt', 'quantity': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == -3
    assert request == before

