import copy
import pytest
from fabops.domain import run


def test_busy_grant_then_reopen_free_resource():
    request = {'resources': ['x', 'y'], 'commands': [{'op': 'acquire', 'resources': ['x'], 'owner': 'a', 'now': 0, 'ttl': 10}, {'op': 'acquire', 'resources': ['y', 'x'], 'owner': 'b', 'now': 1, 'ttl': 10}, {'op': 'restart'}, {'op': 'acquire', 'resources': ['y'], 'owner': 'b', 'now': 2, 'ttl': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'x': 1}, None, 'restarted', {'y': 1}], 'epochs': {'x': 1, 'y': 1}, 'leases': {'x': ['a', 1, 10], 'y': ['b', 1, 12]}, 'outputs': {'x': [0, None], 'y': [0, None]}}
    assert request == before

def test_same_owner_stale_token():
    request = {'resources': ['x', 'y'], 'commands': [{'op': 'acquire', 'resources': ['x'], 'owner': 'a', 'now': 0, 'ttl': 10}, {'op': 'acquire', 'resources': ['x'], 'owner': 'a', 'now': 10, 'ttl': 10}, {'op': 'write', 'tokens': {'x': 1}, 'owner': 'a', 'now': 11, 'expected': {'x': 0}, 'updates': {'x': 'ok'}}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'x': 1}, {'x': 2}, False], 'epochs': {'x': 2, 'y': 0}, 'leases': {'x': ['a', 2, 20]}, 'outputs': {'x': [0, None], 'y': [0, None]}}
    assert request == before

def test_wrong_owner():
    request = {'resources': ['x', 'y'], 'commands': [{'op': 'acquire', 'resources': ['x'], 'owner': 'a', 'now': 0, 'ttl': 10}, {'op': 'write', 'tokens': {'x': 1}, 'owner': 'b', 'now': 1, 'expected': {'x': 0}, 'updates': {'x': 'ok'}}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'x': 1}, False], 'epochs': {'x': 1, 'y': 0}, 'leases': {'x': ['a', 1, 10]}, 'outputs': {'x': [0, None], 'y': [0, None]}}
    assert request == before

def test_expiry_boundary():
    request = {'resources': ['x', 'y'], 'commands': [{'op': 'acquire', 'resources': ['x'], 'owner': 'a', 'now': 0, 'ttl': 10}, {'op': 'write', 'tokens': {'x': 1}, 'owner': 'a', 'now': 10, 'expected': {'x': 0}, 'updates': {'x': 'ok'}}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'x': 1}, False], 'epochs': {'x': 1, 'y': 0}, 'leases': {'x': ['a', 1, 10]}, 'outputs': {'x': [0, None], 'y': [0, None]}}
    assert request == before

def test_renew_never_shortens():
    request = {'resources': ['x', 'y'], 'commands': [{'op': 'acquire', 'resources': ['x'], 'owner': 'a', 'now': 0, 'ttl': 10}, {'op': 'renew', 'tokens': {'x': 1}, 'owner': 'a', 'now': 1, 'ttl': 1}, {'op': 'write', 'tokens': {'x': 1}, 'owner': 'a', 'now': 5, 'expected': {'x': 0}, 'updates': {'x': 'ok'}}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'x': 1}, True, True], 'epochs': {'x': 1, 'y': 0}, 'leases': {'x': ['a', 1, 10]}, 'outputs': {'x': [1, 'ok'], 'y': [0, None]}}
    assert request == before

def test_crashed_acquisition_reuses_uncommitted_epoch():
    request = {'resources': ['x', 'y'], 'commands': [{'op': 'acquire', 'resources': ['x'], 'owner': 'a', 'now': 0, 'ttl': 10, 'crash': True}, {'op': 'restart'}, {'op': 'acquire', 'resources': ['x'], 'owner': 'a', 'now': 2, 'ttl': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['crashed', 'restarted', {'x': 1}], 'epochs': {'x': 1, 'y': 0}, 'leases': {'x': ['a', 1, 12]}, 'outputs': {'x': [0, None], 'y': [0, None]}}
    assert request == before

def test_successful_multiwrite():
    request = {'resources': ['x', 'y'], 'commands': [{'op': 'acquire', 'resources': ['x', 'y'], 'owner': 'a', 'now': 0, 'ttl': 10}, {'op': 'write', 'tokens': {'x': 1, 'y': 1}, 'owner': 'a', 'now': 1, 'expected': {'x': 0, 'y': 0}, 'updates': {'x': 'a', 'y': 'b'}}, {'op': 'restart'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'x': 1, 'y': 1}, True, 'restarted'], 'epochs': {'x': 1, 'y': 1}, 'leases': {'x': ['a', 1, 10], 'y': ['a', 1, 10]}, 'outputs': {'x': [1, 'a'], 'y': [1, 'b']}}
    assert request == before

def test_missing_token_scope():
    request = {'resources': ['x', 'y'], 'commands': [{'op': 'acquire', 'resources': ['x'], 'owner': 'a', 'now': 0, 'ttl': 10}, {'op': 'write', 'tokens': {'x': 1}, 'owner': 'a', 'now': 1, 'expected': {'x': 0, 'y': 0}, 'updates': {'x': 'a', 'y': 'b'}}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'x': 1}, False], 'epochs': {'x': 1, 'y': 0}, 'leases': {'x': ['a', 1, 10]}, 'outputs': {'x': [0, None], 'y': [0, None]}}
    assert request == before

def test_stale_output_revision():
    request = {'resources': ['x', 'y'], 'commands': [{'op': 'acquire', 'resources': ['x'], 'owner': 'a', 'now': 0, 'ttl': 10}, {'op': 'write', 'tokens': {'x': 1}, 'owner': 'a', 'now': 1, 'expected': {'x': 0}, 'updates': {'x': 'ok'}}, {'op': 'write', 'tokens': {'x': 1}, 'owner': 'a', 'now': 2, 'expected': {'x': 0}, 'updates': {'x': 'bad'}}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'x': 1}, True, False], 'epochs': {'x': 1, 'y': 0}, 'leases': {'x': ['a', 1, 10]}, 'outputs': {'x': [1, 'ok'], 'y': [0, None]}}
    assert request == before

def test_crashed_write():
    request = {'resources': ['x', 'y'], 'commands': [{'op': 'acquire', 'resources': ['x'], 'owner': 'a', 'now': 0, 'ttl': 10}, {'op': 'write', 'tokens': {'x': 1}, 'owner': 'a', 'now': 1, 'expected': {'x': 0}, 'updates': {'x': 'ok'}, 'crash': True}, {'op': 'restart'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'x': 1}, 'crashed', 'restarted'], 'epochs': {'x': 1, 'y': 0}, 'leases': {'x': ['a', 1, 10]}, 'outputs': {'x': [0, None], 'y': [0, None]}}
    assert request == before

def test_partial_release_bad_token():
    request = {'resources': ['x', 'y'], 'commands': [{'op': 'acquire', 'resources': ['x', 'y'], 'owner': 'a', 'now': 0, 'ttl': 10}, {'op': 'release', 'tokens': {'x': 1, 'y': 2}, 'owner': 'a', 'now': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'x': 1, 'y': 1}, False], 'epochs': {'x': 1, 'y': 1}, 'leases': {'x': ['a', 1, 10], 'y': ['a', 1, 10]}, 'outputs': {'x': [0, None], 'y': [0, None]}}
    assert request == before

def test_independent_epochs():
    request = {'resources': ['x', 'y'], 'commands': [{'op': 'acquire', 'resources': ['x'], 'owner': 'a', 'now': 0, 'ttl': 10}, {'op': 'release', 'tokens': {'x': 1}, 'owner': 'a', 'now': 1}, {'op': 'acquire', 'resources': ['x', 'y'], 'owner': 'a', 'now': 2, 'ttl': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'x': 1}, True, {'x': 2, 'y': 1}], 'epochs': {'x': 2, 'y': 1}, 'leases': {'x': ['a', 2, 12], 'y': ['a', 1, 12]}, 'outputs': {'x': [0, None], 'y': [0, None]}}
    assert request == before

def test_duplicate_resource_is_set():
    request = {'resources': ['x', 'y'], 'commands': [{'op': 'acquire', 'resources': ['x', 'x'], 'owner': 'a', 'now': 0, 'ttl': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'x': 1}], 'epochs': {'x': 1, 'y': 0}, 'leases': {'x': ['a', 1, 10]}, 'outputs': {'x': [0, None], 'y': [0, None]}}
    assert request == before

def test_crashed_renewal():
    request = {'resources': ['x', 'y'], 'commands': [{'op': 'acquire', 'resources': ['x'], 'owner': 'a', 'now': 0, 'ttl': 10}, {'op': 'renew', 'tokens': {'x': 1}, 'owner': 'a', 'now': 1, 'ttl': 20, 'crash': True}, {'op': 'restart'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'x': 1}, 'crashed', 'restarted'], 'epochs': {'x': 1, 'y': 0}, 'leases': {'x': ['a', 1, 10]}, 'outputs': {'x': [0, None], 'y': [0, None]}}
    assert request == before

def test_crashed_release():
    request = {'resources': ['x', 'y'], 'commands': [{'op': 'acquire', 'resources': ['x'], 'owner': 'a', 'now': 0, 'ttl': 10}, {'op': 'release', 'tokens': {'x': 1}, 'owner': 'a', 'now': 1, 'crash': True}, {'op': 'restart'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'x': 1}, 'crashed', 'restarted'], 'epochs': {'x': 1, 'y': 0}, 'leases': {'x': ['a', 1, 10]}, 'outputs': {'x': [0, None], 'y': [0, None]}}
    assert request == before

def test_validation_precedes_crash():
    request = {'resources': ['x', 'y'], 'commands': [{'op': 'acquire', 'resources': ['x'], 'owner': 'a', 'now': 0, 'ttl': 10}, {'op': 'write', 'tokens': {'x': 9}, 'owner': 'a', 'now': 1, 'expected': {'x': 0}, 'updates': {'x': 'ok'}, 'crash': True}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'x': 1}, False], 'epochs': {'x': 1, 'y': 0}, 'leases': {'x': ['a', 1, 10]}, 'outputs': {'x': [0, None], 'y': [0, None]}}
    assert request == before

def test_independent_reader():
    request = {'resources': ['x', 'y'], 'commands': [{'op': 'acquire', 'resources': ['x'], 'owner': 'a', 'now': 0, 'ttl': 10}, {'op': 'write', 'tokens': {'x': 1}, 'owner': 'a', 'now': 1, 'expected': {'x': 0}, 'updates': {'x': 'ok'}}, {'op': 'read'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'x': 1}, True, {'epochs': {'x': 1, 'y': 0}, 'leases': {'x': ['a', 1, 10]}, 'outputs': {'x': [1, 'ok'], 'y': [0, None]}}], 'epochs': {'x': 1, 'y': 0}, 'leases': {'x': ['a', 1, 10]}, 'outputs': {'x': [1, 'ok'], 'y': [0, None]}}
    assert request == before

