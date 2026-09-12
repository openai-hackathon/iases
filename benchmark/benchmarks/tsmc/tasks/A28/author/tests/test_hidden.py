import copy
import pytest
from fabops.domain import run


def test_reverse_mixed():
    request = {'planned': 16, 'runtime': 8, 'lots': [{'total': 2, 'good': 2, 'ideal_cycle': 3}, {'total': 2, 'good': 2, 'ideal_cycle': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == {'availability': 0.5, 'performance': 1.0, 'quality': 1.0, 'oee': 0.5}
    assert request == before

def test_above_one():
    request = {'planned': 8, 'runtime': 4, 'lots': [{'total': 4, 'good': 4, 'ideal_cycle': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == {'availability': 0.5, 'performance': 2.0, 'quality': 1.0, 'oee': 1.0}
    assert request == before

def test_zero_good():
    request = {'planned': 8, 'runtime': 8, 'lots': [{'total': 4, 'good': 0, 'ideal_cycle': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == {'availability': 1.0, 'performance': 1.0, 'quality': 0.0, 'oee': 0.0}
    assert request == before

def test_all_factors():
    request = {'planned': 16, 'runtime': 8, 'lots': [{'total': 2, 'good': 1, 'ideal_cycle': 1}, {'total': 2, 'good': 1, 'ideal_cycle': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == {'availability': 0.5, 'performance': 0.5, 'quality': 0.5, 'oee': 0.125}
    assert request == before

def test_weighted_cycles():
    request = {'planned': 16, 'runtime': 8, 'lots': [{'total': 1, 'good': 1, 'ideal_cycle': 1}, {'total': 3, 'good': 1, 'ideal_cycle': 5}]}
    before = copy.deepcopy(request)
    assert run(request) == {'availability': 0.5, 'performance': 2.0, 'quality': 0.5, 'oee': 0.5}
    assert request == before

def test_fractional_cycle():
    request = {'planned': 8, 'runtime': 4, 'lots': [{'total': 4, 'good': 2, 'ideal_cycle': 0.5}]}
    before = copy.deepcopy(request)
    assert run(request) == {'availability': 0.5, 'performance': 0.5, 'quality': 0.5, 'oee': 0.125}
    assert request == before

