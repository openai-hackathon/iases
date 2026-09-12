import copy
import pytest
from fabops.domain import run


def test_foreign_release():
    request = {'events': [{'lot': 'a', 'source': 'qa', 'version': 1, 'op': 'hold'}, {'lot': 'a', 'source': 'eng', 'version': 2, 'op': 'release'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'a': ['qa']}
    assert request == before

def test_stale():
    request = {'events': [{'lot': 'a', 'source': 'qa', 'version': 2, 'op': 'hold'}, {'lot': 'a', 'source': 'qa', 'version': 1, 'op': 'release'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'a': ['qa']}
    assert request == before

def test_equal():
    request = {'events': [{'lot': 'a', 'source': 'qa', 'version': 1, 'op': 'hold'}, {'lot': 'a', 'source': 'qa', 'version': 1, 'op': 'release'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'a': ['qa']}
    assert request == before

def test_other_lot():
    request = {'events': [{'lot': 'a', 'source': 'qa', 'version': 1, 'op': 'hold'}, {'lot': 'b', 'source': 'qa', 'version': 1, 'op': 'release'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'a': ['qa'], 'b': []}
    assert request == before

def test_rehold():
    request = {'events': [{'lot': 'a', 'source': 'qa', 'version': 2, 'op': 'release'}, {'lot': 'a', 'source': 'qa', 'version': 3, 'op': 'hold'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'a': ['qa']}
    assert request == before

def test_one_remaining():
    request = {'events': [{'lot': 'a', 'source': 'qa', 'version': 1, 'op': 'hold'}, {'lot': 'a', 'source': 'eng', 'version': 1, 'op': 'hold'}, {'lot': 'a', 'source': 'qa', 'version': 2, 'op': 'release'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'a': ['eng']}
    assert request == before

