import copy
import pytest
from fabops.domain import run


def test_boundary():
    request = {'lease': {'owner': 'a', 'expires': 10}, 'renewals': [{'owner': 'a', 'now': 10, 'ttl': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [False], 'lease': {'owner': 'a', 'expires': 10}}
    assert request == before

def test_after_rejection():
    request = {'lease': {'owner': 'a', 'expires': 10}, 'renewals': [{'owner': 'b', 'now': 5, 'ttl': 20}, {'owner': 'a', 'now': 6, 'ttl': 5}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [False, True], 'lease': {'owner': 'a', 'expires': 11}}
    assert request == before

def test_two_owners():
    request = {'lease': {'owner': 'a', 'expires': 10}, 'renewals': [{'owner': 'b', 'now': 1, 'ttl': 20}, {'owner': 'c', 'now': 2, 'ttl': 20}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [False, False], 'lease': {'owner': 'a', 'expires': 10}}
    assert request == before

def test_shorten():
    request = {'lease': {'owner': 'a', 'expires': 10}, 'renewals': [{'owner': 'a', 'now': 5, 'ttl': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True], 'lease': {'owner': 'a', 'expires': 6}}
    assert request == before

def test_renew_again():
    request = {'lease': {'owner': 'a', 'expires': 10}, 'renewals': [{'owner': 'a', 'now': 9, 'ttl': 5}, {'owner': 'a', 'now': 12, 'ttl': 5}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True, True], 'lease': {'owner': 'a', 'expires': 17}}
    assert request == before

def test_wrong_expired():
    request = {'lease': {'owner': 'a', 'expires': 10}, 'renewals': [{'owner': 'b', 'now': 10, 'ttl': 20}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [False], 'lease': {'owner': 'a', 'expires': 10}}
    assert request == before

