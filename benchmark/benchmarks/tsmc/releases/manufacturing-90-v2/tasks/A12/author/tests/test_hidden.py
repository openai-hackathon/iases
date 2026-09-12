import copy
import pytest
from fabops.domain import run


def test_stations():
    request = {'parts': ['p'], 'stations': ['a', 'b'], 'measurements': [{'part': 'p', 'station': 'a', 'value': 0}, {'part': 'p', 'station': 'b', 'value': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == [{'part': 'p', 'values': [0, 2]}]
    assert request == before

def test_part_order():
    request = {'parts': ['q', 'p'], 'stations': ['s'], 'measurements': [{'part': 'p', 'station': 's', 'value': 0}]}
    before = copy.deepcopy(request)
    assert run(request) == [{'part': 'q', 'values': [None]}, {'part': 'p', 'values': [0]}]
    assert request == before

def test_station_order():
    request = {'parts': ['p'], 'stations': ['b', 'a'], 'measurements': [{'part': 'p', 'station': 'a', 'value': 1}, {'part': 'p', 'station': 'b', 'value': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == [{'part': 'p', 'values': [2, 1]}]
    assert request == before

def test_null():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'part': 'p', 'station': 's', 'value': None}]}
    before = copy.deepcopy(request)
    assert run(request) == [{'part': 'p', 'values': [None]}]
    assert request == before

def test_ignore():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'part': 'q', 'station': 's', 'value': 4}]}
    before = copy.deepcopy(request)
    assert run(request) == [{'part': 'p', 'values': [None]}]
    assert request == before

def test_no_stations():
    request = {'parts': ['p'], 'stations': [], 'measurements': []}
    before = copy.deepcopy(request)
    assert run(request) == [{'part': 'p', 'values': []}]
    assert request == before

