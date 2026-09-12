import copy
import pytest
from fabops.domain import run


def test_pending_intent():
    request = {'commands': [{'op': 'enqueue', 'event': {'id': 'e1', 'artifact': 'lot', 'revision': 1, 'payload': 'a'}, 'crash': False}, {'op': 'restart'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['queued', 'restarted'], 'pending': [['e1', 'vds'], ['e1', 'qdr'], ['e1', 'tdp']], 'projections': {'vds': {}, 'qdr': {}, 'tdp': {}}, 'receipts': 0}
    assert request == before

def test_pre_sink_recovery():
    request = {'commands': [{'op': 'enqueue', 'event': {'id': 'e1', 'artifact': 'lot', 'revision': 1, 'payload': 'a'}, 'crash': False}, {'op': 'deliver', 'id': 'e1', 'channel': 'qdr', 'crash': 'before_sink'}, {'op': 'restart'}, {'op': 'reconcile'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['queued', 'crashed', 'restarted', 'reconciled'], 'pending': [], 'projections': {'vds': {'lot': [1, 'a']}, 'qdr': {'lot': [1, 'a']}, 'tdp': {'lot': [1, 'a']}}, 'receipts': 3}
    assert request == before

def test_lost_ack_unreconciled():
    request = {'commands': [{'op': 'enqueue', 'event': {'id': 'e1', 'artifact': 'lot', 'revision': 1, 'payload': 'a'}, 'crash': False}, {'op': 'deliver', 'id': 'e1', 'channel': 'qdr', 'crash': 'after_sink'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['queued', 'crashed'], 'pending': [['e1', 'vds'], ['e1', 'qdr'], ['e1', 'tdp']], 'projections': {'vds': {}, 'qdr': {'lot': [1, 'a']}, 'tdp': {}}, 'receipts': 1}
    assert request == before

def test_one_channel_only():
    request = {'commands': [{'op': 'enqueue', 'event': {'id': 'e1', 'artifact': 'lot', 'revision': 1, 'payload': 'a'}, 'crash': False}, {'op': 'deliver', 'id': 'e1', 'channel': 'qdr', 'crash': 'none'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['queued', 'acked'], 'pending': [['e1', 'vds'], ['e1', 'tdp']], 'projections': {'vds': {}, 'qdr': {'lot': [1, 'a']}, 'tdp': {}}, 'receipts': 1}
    assert request == before

def test_acked_retry():
    request = {'commands': [{'op': 'enqueue', 'event': {'id': 'e1', 'artifact': 'lot', 'revision': 1, 'payload': 'a'}, 'crash': False}, {'op': 'deliver', 'id': 'e1', 'channel': 'qdr', 'crash': 'none'}, {'op': 'deliver', 'id': 'e1', 'channel': 'qdr', 'crash': 'none'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['queued', 'acked', 'acked'], 'pending': [['e1', 'vds'], ['e1', 'tdp']], 'projections': {'vds': {}, 'qdr': {'lot': [1, 'a']}, 'tdp': {}}, 'receipts': 1}
    assert request == before

def test_two_lost_acks():
    request = {'commands': [{'op': 'enqueue', 'event': {'id': 'e1', 'artifact': 'lot', 'revision': 1, 'payload': 'a'}, 'crash': False}, {'op': 'deliver', 'id': 'e1', 'channel': 'qdr', 'crash': 'after_sink'}, {'op': 'deliver', 'id': 'e1', 'channel': 'qdr', 'crash': 'after_sink'}, {'op': 'deliver', 'id': 'e1', 'channel': 'qdr', 'crash': 'none'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['queued', 'crashed', 'crashed', 'acked'], 'pending': [['e1', 'vds'], ['e1', 'tdp']], 'projections': {'vds': {}, 'qdr': {'lot': [1, 'a']}, 'tdp': {}}, 'receipts': 1}
    assert request == before

def test_older_reconciled_last():
    request = {'commands': [{'op': 'enqueue', 'event': {'id': 'z', 'artifact': 'lot', 'revision': 1, 'payload': 'old'}, 'crash': False}, {'op': 'enqueue', 'event': {'id': 'a', 'artifact': 'lot', 'revision': 2, 'payload': 'new'}, 'crash': False}, {'op': 'reconcile'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['queued', 'queued', 'reconciled'], 'pending': [], 'projections': {'vds': {'lot': [2, 'new']}, 'qdr': {'lot': [2, 'new']}, 'tdp': {'lot': [2, 'new']}}, 'receipts': 6}
    assert request == before

def test_stale_lost_ack():
    request = {'commands': [{'op': 'enqueue', 'event': {'id': 'e1', 'artifact': 'lot', 'revision': 1, 'payload': 'a'}, 'crash': False}, {'op': 'enqueue', 'event': {'id': 'e2', 'artifact': 'lot', 'revision': 2, 'payload': 'new'}, 'crash': False}, {'op': 'deliver', 'id': 'e2', 'channel': 'qdr', 'crash': 'none'}, {'op': 'deliver', 'id': 'e1', 'channel': 'qdr', 'crash': 'after_sink'}, {'op': 'restart'}, {'op': 'reconcile'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['queued', 'queued', 'acked', 'crashed', 'restarted', 'reconciled'], 'pending': [], 'projections': {'vds': {'lot': [2, 'new']}, 'qdr': {'lot': [2, 'new']}, 'tdp': {'lot': [2, 'new']}}, 'receipts': 6}
    assert request == before

def test_conflicting_id():
    request = {'commands': [{'op': 'enqueue', 'event': {'id': 'e1', 'artifact': 'lot', 'revision': 1, 'payload': 'a'}, 'crash': False}, {'op': 'enqueue', 'event': {'id': 'e1', 'artifact': 'lot', 'revision': 1, 'payload': 'bad'}, 'crash': False}, {'op': 'reconcile'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['queued', 'conflict', 'reconciled'], 'pending': [], 'projections': {'vds': {'lot': [1, 'a']}, 'qdr': {'lot': [1, 'a']}, 'tdp': {'lot': [1, 'a']}}, 'receipts': 3}
    assert request == before

def test_duplicate_enqueue():
    request = {'commands': [{'op': 'enqueue', 'event': {'id': 'e1', 'artifact': 'lot', 'revision': 1, 'payload': 'a'}, 'crash': False}, {'op': 'enqueue', 'event': {'id': 'e1', 'artifact': 'lot', 'revision': 1, 'payload': 'a'}, 'crash': False}, {'op': 'reconcile'}, {'op': 'reconcile'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['queued', 'duplicate', 'reconciled', 'reconciled'], 'pending': [], 'projections': {'vds': {'lot': [1, 'a']}, 'qdr': {'lot': [1, 'a']}, 'tdp': {'lot': [1, 'a']}}, 'receipts': 3}
    assert request == before

def test_missing_delivery():
    request = {'commands': [{'op': 'deliver', 'id': 'absent', 'channel': 'qdr', 'crash': 'none'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['missing'], 'pending': [], 'projections': {'vds': {}, 'qdr': {}, 'tdp': {}}, 'receipts': 0}
    assert request == before

def test_failed_intent_retry():
    request = {'commands': [{'op': 'enqueue', 'event': {'id': 'e1', 'artifact': 'lot', 'revision': 1, 'payload': 'a'}, 'crash': True}, {'op': 'enqueue', 'event': {'id': 'e1', 'artifact': 'lot', 'revision': 1, 'payload': 'a'}, 'crash': False}, {'op': 'reconcile'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['crashed', 'queued', 'reconciled'], 'pending': [], 'projections': {'vds': {'lot': [1, 'a']}, 'qdr': {'lot': [1, 'a']}, 'tdp': {'lot': [1, 'a']}}, 'receipts': 3}
    assert request == before

def test_independent_artifacts():
    request = {'commands': [{'op': 'enqueue', 'event': {'id': 'e1', 'artifact': 'lot', 'revision': 1, 'payload': 'a'}, 'crash': False}, {'op': 'enqueue', 'event': {'id': 'e2', 'artifact': 'tool', 'revision': 1, 'payload': 'b'}, 'crash': False}, {'op': 'reconcile'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['queued', 'queued', 'reconciled'], 'pending': [], 'projections': {'vds': {'lot': [1, 'a'], 'tool': [1, 'b']}, 'qdr': {'lot': [1, 'a'], 'tool': [1, 'b']}, 'tdp': {'lot': [1, 'a'], 'tool': [1, 'b']}}, 'receipts': 6}
    assert request == before

