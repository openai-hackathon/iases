import copy
import pytest
from fabops.domain import run


def test_recipes():
    request = {'capacity': 4, 'lots': [{'id': '0', 'product': 'p', 'recipe': 'a', 'reticle': 't', 'units': 1}, {'id': '1', 'product': 'p', 'recipe': 'b', 'reticle': 't', 'units': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == [['0'], ['1']]
    assert request == before

def test_products():
    request = {'capacity': 4, 'lots': [{'id': '0', 'product': 'a', 'recipe': 'r', 'reticle': 't', 'units': 1}, {'id': '1', 'product': 'b', 'recipe': 'r', 'reticle': 't', 'units': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == [['0'], ['1']]
    assert request == before

def test_full():
    request = {'capacity': 4, 'lots': [{'id': '0', 'product': 'p', 'recipe': 'r', 'reticle': 't', 'units': 4}, {'id': '1', 'product': 'p', 'recipe': 'r', 'reticle': 't', 'units': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == [['0'], ['1']]
    assert request == before

def test_return_to_reticle():
    request = {'capacity': 4, 'lots': [{'id': '0', 'product': 'p', 'recipe': 'r', 'reticle': 'a', 'units': 1}, {'id': '1', 'product': 'p', 'recipe': 'r', 'reticle': 'b', 'units': 1}, {'id': '2', 'product': 'p', 'recipe': 'r', 'reticle': 'a', 'units': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == [['0', '2'], ['1']]
    assert request == before

def test_first_fit():
    request = {'capacity': 4, 'lots': [{'id': '0', 'product': 'p', 'recipe': 'r', 'reticle': 't', 'units': 3}, {'id': '1', 'product': 'p', 'recipe': 'r', 'reticle': 't', 'units': 2}, {'id': '2', 'product': 'p', 'recipe': 'r', 'reticle': 't', 'units': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == [['0', '2'], ['1']]
    assert request == before

def test_three_reticles():
    request = {'capacity': 4, 'lots': [{'id': '0', 'product': 'p', 'recipe': 'r', 'reticle': 'a', 'units': 1}, {'id': '1', 'product': 'p', 'recipe': 'r', 'reticle': 'b', 'units': 1}, {'id': '2', 'product': 'p', 'recipe': 'r', 'reticle': 'c', 'units': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == [['0'], ['1'], ['2']]
    assert request == before

