import copy
import pytest
from fabops.domain import run


def test_fractional():
    request = {'mono_start': 2, 'mono_end': 2.5, 'wall_start': 100, 'wall_end': 100.5}
    before = copy.deepcopy(request)
    assert run(request) == 0.5
    assert request == before

def test_frozen_wall():
    request = {'mono_start': 2, 'mono_end': 7, 'wall_start': 100, 'wall_end': 100}
    before = copy.deepcopy(request)
    assert run(request) == 5
    assert request == before

def test_large_epoch():
    request = {'mono_start': 1000, 'mono_end': 1003, 'wall_start': 1000000, 'wall_end': 1000100}
    before = copy.deepcopy(request)
    assert run(request) == 3
    assert request == before

def test_repeated_backward():
    request = {'mono_start': 0, 'mono_end': 4, 'wall_start': 100, 'wall_end': 99}
    before = copy.deepcopy(request)
    assert run(request) == 4
    assert request == before

def test_offset_independent():
    request = {'mono_start': 50, 'mono_end': 60, 'wall_start': 0, 'wall_end': 10}
    before = copy.deepcopy(request)
    assert run(request) == 10
    assert request == before

def test_negative_wall():
    request = {'mono_start': 0, 'mono_end': 1, 'wall_start': -2, 'wall_end': -4}
    before = copy.deepcopy(request)
    assert run(request) == 1
    assert request == before

