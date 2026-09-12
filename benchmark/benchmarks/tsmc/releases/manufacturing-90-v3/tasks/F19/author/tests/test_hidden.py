import copy
import pytest
from fabops.domain import run


def test_stale_inventory():
    request = {'lots': [{'id': 'a', 'priority': 1, 'reticle': 'r', 'costs': {'x': 1}}], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'observed': {'dispatch': 1, 'inventory': 1}, 'current': {'dispatch': 1, 'inventory': 2}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [['a', 'x']], 'committed': False, 'stock': {'r': 1, 's': 1}}
    assert request == before

def test_stale_empty():
    request = {'lots': [], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'observed': {'dispatch': 1, 'inventory': 1}, 'current': {'dispatch': 1, 'inventory': 2}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [], 'committed': False, 'stock': {'r': 1, 's': 1}}
    assert request == before

def test_priority():
    request = {'lots': [{'id': 'a', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0}}, {'id': 'b', 'priority': 2, 'reticle': 'r', 'costs': {'x': 1}}], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'observed': {'dispatch': 1, 'inventory': 1}, 'current': {'dispatch': 1, 'inventory': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [['b', 'x']], 'committed': True, 'stock': {'r': 0, 's': 1}}
    assert request == before

def test_cost():
    request = {'lots': [{'id': 'a', 'priority': 1, 'reticle': 'r', 'costs': {'x': 3, 'y': 1}}], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'observed': {'dispatch': 1, 'inventory': 1}, 'current': {'dispatch': 1, 'inventory': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [['a', 'y']], 'committed': True, 'stock': {'r': 0, 's': 1}}
    assert request == before

def test_tie():
    request = {'lots': [{'id': 'b', 'priority': 1, 'reticle': 'r', 'costs': {'y': 1}}, {'id': 'a', 'priority': 1, 'reticle': 'r', 'costs': {'x': 1}}], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'observed': {'dispatch': 1, 'inventory': 1}, 'current': {'dispatch': 1, 'inventory': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [['a', 'x']], 'committed': True, 'stock': {'r': 0, 's': 1}}
    assert request == before

def test_cardinality_reverse():
    request = {'lots': [{'id': 'c', 'priority': 1, 'reticle': 's', 'costs': {'x': 0}}, {'id': 'b', 'priority': 1, 'reticle': 'r', 'costs': {'y': 0}}, {'id': 'a', 'priority': 99, 'reticle': 'r', 'costs': {'x': 0}}], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'observed': {'dispatch': 1, 'inventory': 1}, 'current': {'dispatch': 1, 'inventory': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [['b', 'y'], ['c', 'x']], 'committed': True, 'stock': {'r': 0, 's': 0}}
    assert request == before

def test_missing_stock():
    request = {'lots': [{'id': 'a', 'priority': 1, 'reticle': 'missing', 'costs': {'x': 0}}], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'observed': {'dispatch': 1, 'inventory': 1}, 'current': {'dispatch': 1, 'inventory': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [], 'committed': True, 'stock': {'r': 1, 's': 1}}
    assert request == before

def test_assignment_alternative():
    request = {'lots': [{'id': 'a', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0, 'y': 1}}, {'id': 'b', 'priority': 1, 'reticle': 's', 'costs': {'x': 0}}], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'observed': {'dispatch': 1, 'inventory': 1}, 'current': {'dispatch': 1, 'inventory': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [['a', 'y'], ['b', 'x']], 'committed': True, 'stock': {'r': 0, 's': 0}}
    assert request == before

