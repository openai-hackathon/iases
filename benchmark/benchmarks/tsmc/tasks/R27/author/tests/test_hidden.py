import copy
import pytest
from fabops.domain import run


def test_unstarted():
    request = {'records': [{'id': '0', 'offset': 0}, {'id': '1', 'offset': 1}], 'consumers': [{'active': True, 'ack': -1}, {'active': True, 'ack': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == ['0', '1']
    assert request == before

def test_inactive():
    request = {'records': [{'id': '0', 'offset': 0}, {'id': '1', 'offset': 1}, {'id': '2', 'offset': 2}], 'consumers': [{'active': True, 'ack': 1}, {'active': False, 'ack': -1}]}
    before = copy.deepcopy(request)
    assert run(request) == ['2']
    assert request == before

def test_all_inactive():
    request = {'records': [{'id': '0', 'offset': 0}, {'id': '1', 'offset': 1}], 'consumers': [{'active': False, 'ack': 5}]}
    before = copy.deepcopy(request)
    assert run(request) == ['0', '1']
    assert request == before

def test_equal():
    request = {'records': [{'id': '0', 'offset': 0}, {'id': '1', 'offset': 1}, {'id': '2', 'offset': 2}], 'consumers': [{'active': True, 'ack': 1}, {'active': True, 'ack': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == ['2']
    assert request == before

def test_input_order():
    request = {'records': [{'id': '0', 'offset': 3}, {'id': '1', 'offset': 1}, {'id': '2', 'offset': 2}], 'consumers': [{'active': True, 'ack': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == ['0', '2']
    assert request == before

def test_three_consumers():
    request = {'records': [{'id': '0', 'offset': 0}, {'id': '1', 'offset': 1}, {'id': '2', 'offset': 2}, {'id': '3', 'offset': 3}], 'consumers': [{'active': True, 'ack': 3}, {'active': True, 'ack': 1}, {'active': True, 'ack': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == ['2', '3']
    assert request == before

