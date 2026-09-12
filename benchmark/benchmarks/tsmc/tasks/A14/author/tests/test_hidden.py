import copy
import pytest
from fabops.domain import run


def test_before():
    request = {'calibrations': [{'effective': 2, 'gain': 2, 'offset': 1}], 'samples': [[1, 3]]}
    before = copy.deepcopy(request)
    assert run(request) == [None]
    assert request == before

def test_latest():
    request = {'calibrations': [{'effective': 0, 'gain': 1, 'offset': 0}, {'effective': 2, 'gain': 2, 'offset': 1}], 'samples': [[3, 3]]}
    before = copy.deepcopy(request)
    assert run(request) == [7]
    assert request == before

def test_unsorted():
    request = {'calibrations': [{'effective': 2, 'gain': 2, 'offset': 1}, {'effective': 0, 'gain': 1, 'offset': 0}], 'samples': [[1, 3], [3, 3]]}
    before = copy.deepcopy(request)
    assert run(request) == [3, 7]
    assert request == before

def test_boundary():
    request = {'calibrations': [{'effective': 0, 'gain': 1, 'offset': 0}, {'effective': 2, 'gain': 2, 'offset': 1}], 'samples': [[2, 3]]}
    before = copy.deepcopy(request)
    assert run(request) == [7]
    assert request == before

def test_zero_gain():
    request = {'calibrations': [{'effective': 0, 'gain': 0, 'offset': 5}], 'samples': [[1, 9]]}
    before = copy.deepcopy(request)
    assert run(request) == [5]
    assert request == before

def test_sample_order():
    request = {'calibrations': [{'effective': 0, 'gain': 1, 'offset': 0}, {'effective': 2, 'gain': 2, 'offset': 1}], 'samples': [[3, 2], [1, 2]]}
    before = copy.deepcopy(request)
    assert run(request) == [5, 2]
    assert request == before

