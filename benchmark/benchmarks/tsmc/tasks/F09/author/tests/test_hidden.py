import copy
import pytest
from fabops.domain import run


def test_quantity_1_capacity_25():
    request = {'quantity': 1, 'capacity': 25}
    before = copy.deepcopy(request)
    assert run(request) == 1
    assert request == before

def test_quantity_49_capacity_25():
    request = {'quantity': 49, 'capacity': 25}
    before = copy.deepcopy(request)
    assert run(request) == 2
    assert request == before

def test_quantity_51_capacity_25():
    request = {'quantity': 51, 'capacity': 25}
    before = copy.deepcopy(request)
    assert run(request) == 3
    assert request == before

def test_quantity_1000001_capacity_1000():
    request = {'quantity': 1000001, 'capacity': 1000}
    before = copy.deepcopy(request)
    assert run(request) == 1001
    assert request == before

def test_quantity_7_capacity_1():
    request = {'quantity': 7, 'capacity': 1}
    before = copy.deepcopy(request)
    assert run(request) == 7
    assert request == before

def test_quantity_0_capacity_1():
    request = {'quantity': 0, 'capacity': 1}
    before = copy.deepcopy(request)
    assert run(request) == 0
    assert request == before

