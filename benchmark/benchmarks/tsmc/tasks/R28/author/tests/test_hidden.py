import copy
import pytest
from fabops.domain import run


def test_bad_crc_inside():
    request = {'lines': ['1|a|00000000', '2|b|f898de62']}
    before = copy.deepcopy(request)
    with pytest.raises(ValueError):
        run(request)
    assert request == before

def test_bad_crc_tail():
    request = {'lines': ['1|a|63d73181', '2|b|00000000']}
    before = copy.deepcopy(request)
    assert run(request) == ['a']
    assert request == before

def test_gap():
    request = {'lines': ['1|a|63d73181', '3|c|8e5d84c3']}
    before = copy.deepcopy(request)
    with pytest.raises(ValueError):
        run(request)
    assert request == before

def test_duplicate():
    request = {'lines': ['1|a|63d73181', '1|a|63d73181']}
    before = copy.deepcopy(request)
    with pytest.raises(ValueError):
        run(request)
    assert request == before

def test_valid_tail():
    request = {'lines': ['1|a|63d73181', '2|b|f898de62', '3|c|8e5d84c3']}
    before = copy.deepcopy(request)
    assert run(request) == ['a', 'b', 'c']
    assert request == before

def test_first_sequence():
    request = {'lines': ['2|b|f898de62']}
    before = copy.deepcopy(request)
    with pytest.raises(ValueError):
        run(request)
    assert request == before

