import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'commands': []}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [], 'next_sequence': 1, 'total': 0, 'epoch': 0, 'compacted': 0, 'lease': None, 'consumers': {'mes': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}, 'quality': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}}, 'retained': [], 'acks': [], 'commands': 0}
    assert request == before

def test_append_only():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1], 'next_sequence': 2, 'total': 5, 'epoch': 0, 'compacted': 0, 'lease': None, 'consumers': {'mes': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}, 'quality': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}}, 'retained': [1], 'acks': [], 'commands': 1}
    assert request == before

def test_failed_append_has_no_durable_state():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': True}, {'op': 'restart'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['crashed', 'restarted'], 'next_sequence': 1, 'total': 0, 'epoch': 0, 'compacted': 0, 'lease': None, 'consumers': {'mes': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}, 'quality': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}}, 'retained': [], 'acks': [], 'commands': 0}
    assert request == before

def test_failed_append_retry_uses_sequence_one():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': True}, {'op': 'restart'}, {'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 100}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['crashed', 'restarted', 1, 1, 'acked'], 'next_sequence': 2, 'total': 5, 'epoch': 1, 'compacted': 0, 'lease': ['w', 1, 100], 'consumers': {'mes': {'next': 2, 'total': 5, 'trail': ['e1'], 'buffered': []}, 'quality': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}}, 'retained': [1], 'acks': [[1, 'mes']], 'commands': 1}
    assert request == before

def test_before_sink_crash_has_no_ack():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 100}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'before_sink'}, {'op': 'restart'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 1, 'crashed', 'restarted'], 'next_sequence': 2, 'total': 5, 'epoch': 1, 'compacted': 0, 'lease': ['w', 1, 100], 'consumers': {'mes': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}, 'quality': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}}, 'retained': [1], 'acks': [], 'commands': 1}
    assert request == before

def test_before_sink_retry_delivers():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 100}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'before_sink'}, {'op': 'restart'}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 1, 'crashed', 'restarted', 'acked'], 'next_sequence': 2, 'total': 5, 'epoch': 1, 'compacted': 0, 'lease': ['w', 1, 100], 'consumers': {'mes': {'next': 2, 'total': 5, 'trail': ['e1'], 'buffered': []}, 'quality': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}}, 'retained': [1], 'acks': [[1, 'mes']], 'commands': 1}
    assert request == before

def test_after_sink_only():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 100}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'after_sink'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 1, 'crashed'], 'next_sequence': 2, 'total': 5, 'epoch': 1, 'compacted': 0, 'lease': ['w', 1, 100], 'consumers': {'mes': {'next': 2, 'total': 5, 'trail': ['e1'], 'buffered': []}, 'quality': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}}, 'retained': [1], 'acks': [], 'commands': 1}
    assert request == before

def test_gap_buffer_is_observable():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'append', 'id': 'e2', 'delta': 7, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 100}, {'op': 'deliver', 'seq': 2, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 2, 1, 'acked'], 'next_sequence': 3, 'total': 12, 'epoch': 1, 'compacted': 0, 'lease': ['w', 1, 100], 'consumers': {'mes': {'next': 1, 'total': 0, 'trail': [], 'buffered': [2]}, 'quality': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}}, 'retained': [1, 2], 'acks': [[2, 'mes']], 'commands': 2}
    assert request == before

def test_two_gaps_drain_in_sequence():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'append', 'id': 'e2', 'delta': 7, 'crash': False}, {'op': 'append', 'id': 'e3', 'delta': -2, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 100}, {'op': 'deliver', 'seq': 3, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'deliver', 'seq': 2, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'restart'}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 2, 3, 1, 'acked', 'acked', 'restarted', 'acked'], 'next_sequence': 4, 'total': 10, 'epoch': 1, 'compacted': 0, 'lease': ['w', 1, 100], 'consumers': {'mes': {'next': 4, 'total': 10, 'trail': ['e1', 'e2', 'e3'], 'buffered': []}, 'quality': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}}, 'retained': [1, 2, 3], 'acks': [[1, 'mes'], [2, 'mes'], [3, 'mes']], 'commands': 3}
    assert request == before

def test_buffered_lost_ack_is_not_double_applied():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'append', 'id': 'e2', 'delta': 7, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 100}, {'op': 'deliver', 'seq': 2, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'after_sink'}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'restart'}, {'op': 'deliver', 'seq': 2, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 2, 1, 'crashed', 'acked', 'restarted', 'acked'], 'next_sequence': 3, 'total': 12, 'epoch': 1, 'compacted': 0, 'lease': ['w', 1, 100], 'consumers': {'mes': {'next': 3, 'total': 12, 'trail': ['e1', 'e2'], 'buffered': []}, 'quality': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}}, 'retained': [1, 2], 'acks': [[1, 'mes'], [2, 'mes']], 'commands': 2}
    assert request == before

def test_acknowledged_retry_is_noop():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 100}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'restart'}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 1, 'acked', 'acked', 'restarted', 'acked'], 'next_sequence': 2, 'total': 5, 'epoch': 1, 'compacted': 0, 'lease': ['w', 1, 100], 'consumers': {'mes': {'next': 2, 'total': 5, 'trail': ['e1'], 'buffered': []}, 'quality': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}}, 'retained': [1], 'acks': [[1, 'mes']], 'commands': 1}
    assert request == before

def test_lease_blocks_concurrent_acquire():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 100}, {'op': 'acquire', 'owner': 'other', 'now': 1, 'ttl': 100}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 1, None], 'next_sequence': 2, 'total': 5, 'epoch': 1, 'compacted': 0, 'lease': ['w', 1, 100], 'consumers': {'mes': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}, 'quality': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}}, 'retained': [1], 'acks': [], 'commands': 1}
    assert request == before

def test_wrong_owner_fenced():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 100}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'other', 'token': 1, 'now': 0, 'crash': 'none'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 1, 'fenced'], 'next_sequence': 2, 'total': 5, 'epoch': 1, 'compacted': 0, 'lease': ['w', 1, 100], 'consumers': {'mes': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}, 'quality': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}}, 'retained': [1], 'acks': [], 'commands': 1}
    assert request == before

def test_same_owner_stale_token_fenced():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 2}, {'op': 'acquire', 'owner': 'w', 'now': 2, 'ttl': 100}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 2, 'crash': 'none'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 1, 2, 'fenced'], 'next_sequence': 2, 'total': 5, 'epoch': 2, 'compacted': 0, 'lease': ['w', 2, 102], 'consumers': {'mes': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}, 'quality': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}}, 'retained': [1], 'acks': [], 'commands': 1}
    assert request == before

def test_expiry_boundary_fenced():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 2}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 2, 'crash': 'none'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 1, 'fenced'], 'next_sequence': 2, 'total': 5, 'epoch': 1, 'compacted': 0, 'lease': ['w', 1, 2], 'consumers': {'mes': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}, 'quality': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}}, 'retained': [1], 'acks': [], 'commands': 1}
    assert request == before

def test_retired_epoch_survives_restart():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 100}, {'op': 'retire', 'owner': 'w', 'token': 1, 'now': 0}, {'op': 'restart'}, {'op': 'acquire', 'owner': 'w', 'now': 1, 'ttl': 100}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 1, 'crash': 'none'}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 2, 'now': 1, 'crash': 'none'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 1, 'retired', 'restarted', 2, 'fenced', 'acked'], 'next_sequence': 2, 'total': 5, 'epoch': 2, 'compacted': 0, 'lease': ['w', 2, 101], 'consumers': {'mes': {'next': 2, 'total': 5, 'trail': ['e1'], 'buffered': []}, 'quality': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}}, 'retained': [1], 'acks': [[1, 'mes']], 'commands': 1}
    assert request == before

def test_wrong_token_cannot_retire():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 100}, {'op': 'retire', 'owner': 'w', 'token': 9, 'now': 0}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 1, 'fenced', 'acked'], 'next_sequence': 2, 'total': 5, 'epoch': 1, 'compacted': 0, 'lease': ['w', 1, 100], 'consumers': {'mes': {'next': 2, 'total': 5, 'trail': ['e1'], 'buffered': []}, 'quality': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}}, 'retained': [1], 'acks': [[1, 'mes']], 'commands': 1}
    assert request == before

def test_fully_consumed_compaction():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 100}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'deliver', 'seq': 1, 'consumer': 'quality', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'compact', 'owner': 'w', 'token': 1, 'now': 0, 'crash': False}, {'op': 'restart'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 1, 'acked', 'acked', 1, 'restarted'], 'next_sequence': 2, 'total': 5, 'epoch': 1, 'compacted': 1, 'lease': ['w', 1, 100], 'consumers': {'mes': {'next': 2, 'total': 5, 'trail': ['e1'], 'buffered': []}, 'quality': {'next': 2, 'total': 5, 'trail': ['e1'], 'buffered': []}}, 'retained': [], 'acks': [], 'commands': 1}
    assert request == before

def test_lost_ack_prevents_compaction():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 100}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'after_sink'}, {'op': 'deliver', 'seq': 1, 'consumer': 'quality', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'compact', 'owner': 'w', 'token': 1, 'now': 0, 'crash': False}, {'op': 'restart'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 1, 'crashed', 'acked', 0, 'restarted'], 'next_sequence': 2, 'total': 5, 'epoch': 1, 'compacted': 0, 'lease': ['w', 1, 100], 'consumers': {'mes': {'next': 2, 'total': 5, 'trail': ['e1'], 'buffered': []}, 'quality': {'next': 2, 'total': 5, 'trail': ['e1'], 'buffered': []}}, 'retained': [1], 'acks': [[1, 'quality']], 'commands': 1}
    assert request == before

def test_ack_repair_then_compaction():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 100}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'after_sink'}, {'op': 'deliver', 'seq': 1, 'consumer': 'quality', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'compact', 'owner': 'w', 'token': 1, 'now': 0, 'crash': False}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'compact', 'owner': 'w', 'token': 1, 'now': 0, 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 1, 'crashed', 'acked', 0, 'acked', 1], 'next_sequence': 2, 'total': 5, 'epoch': 1, 'compacted': 1, 'lease': ['w', 1, 100], 'consumers': {'mes': {'next': 2, 'total': 5, 'trail': ['e1'], 'buffered': []}, 'quality': {'next': 2, 'total': 5, 'trail': ['e1'], 'buffered': []}}, 'retained': [], 'acks': [], 'commands': 1}
    assert request == before

def test_compaction_crash_rolls_back_payloads_and_cut():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 100}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'deliver', 'seq': 1, 'consumer': 'quality', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'compact', 'owner': 'w', 'token': 1, 'now': 0, 'crash': True}, {'op': 'restart'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 1, 'acked', 'acked', 'crashed', 'restarted'], 'next_sequence': 2, 'total': 5, 'epoch': 1, 'compacted': 0, 'lease': ['w', 1, 100], 'consumers': {'mes': {'next': 2, 'total': 5, 'trail': ['e1'], 'buffered': []}, 'quality': {'next': 2, 'total': 5, 'trail': ['e1'], 'buffered': []}}, 'retained': [1], 'acks': [[1, 'mes'], [1, 'quality']], 'commands': 1}
    assert request == before

def test_compacted_identity_still_deduplicates():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 100}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'deliver', 'seq': 1, 'consumer': 'quality', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'compact', 'owner': 'w', 'token': 1, 'now': 0, 'crash': False}, {'op': 'restart'}, {'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 1, 'acked', 'acked', 1, 'restarted', 1], 'next_sequence': 2, 'total': 5, 'epoch': 1, 'compacted': 1, 'lease': ['w', 1, 100], 'consumers': {'mes': {'next': 2, 'total': 5, 'trail': ['e1'], 'buffered': []}, 'quality': {'next': 2, 'total': 5, 'trail': ['e1'], 'buffered': []}}, 'retained': [], 'acks': [], 'commands': 1}
    assert request == before

def test_compacted_identity_rejects_changed_body():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 100}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'deliver', 'seq': 1, 'consumer': 'quality', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'compact', 'owner': 'w', 'token': 1, 'now': 0, 'crash': False}, {'op': 'append', 'id': 'e1', 'delta': 9, 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 1, 'acked', 'acked', 1, 'conflict'], 'next_sequence': 2, 'total': 5, 'epoch': 1, 'compacted': 1, 'lease': ['w', 1, 100], 'consumers': {'mes': {'next': 2, 'total': 5, 'trail': ['e1'], 'buffered': []}, 'quality': {'next': 2, 'total': 5, 'trail': ['e1'], 'buffered': []}}, 'retained': [], 'acks': [], 'commands': 1}
    assert request == before

def test_append_after_compaction_preserves_sequence():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 100}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'deliver', 'seq': 1, 'consumer': 'quality', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'compact', 'owner': 'w', 'token': 1, 'now': 0, 'crash': False}, {'op': 'append', 'id': 'e2', 'delta': 7, 'crash': False}, {'op': 'deliver', 'seq': 2, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'deliver', 'seq': 2, 'consumer': 'quality', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 1, 'acked', 'acked', 1, 2, 'acked', 'acked'], 'next_sequence': 3, 'total': 12, 'epoch': 1, 'compacted': 1, 'lease': ['w', 1, 100], 'consumers': {'mes': {'next': 3, 'total': 12, 'trail': ['e1', 'e2'], 'buffered': []}, 'quality': {'next': 3, 'total': 12, 'trail': ['e1', 'e2'], 'buffered': []}}, 'retained': [2], 'acks': [[2, 'mes'], [2, 'quality']], 'commands': 2}
    assert request == before

def test_compact_only_common_applied_prefix():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'append', 'id': 'e2', 'delta': 7, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 100}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'deliver', 'seq': 2, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'deliver', 'seq': 1, 'consumer': 'quality', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'compact', 'owner': 'w', 'token': 1, 'now': 0, 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 2, 1, 'acked', 'acked', 'acked', 1], 'next_sequence': 3, 'total': 12, 'epoch': 1, 'compacted': 1, 'lease': ['w', 1, 100], 'consumers': {'mes': {'next': 3, 'total': 12, 'trail': ['e1', 'e2'], 'buffered': []}, 'quality': {'next': 2, 'total': 5, 'trail': ['e1'], 'buffered': []}}, 'retained': [2], 'acks': [[2, 'mes']], 'commands': 2}
    assert request == before

def test_both_acknowledged_gap_still_not_compactable():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'append', 'id': 'e2', 'delta': 7, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 100}, {'op': 'deliver', 'seq': 2, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'deliver', 'seq': 2, 'consumer': 'quality', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'compact', 'owner': 'w', 'token': 1, 'now': 0, 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 2, 1, 'acked', 'acked', 0], 'next_sequence': 3, 'total': 12, 'epoch': 1, 'compacted': 0, 'lease': ['w', 1, 100], 'consumers': {'mes': {'next': 1, 'total': 0, 'trail': [], 'buffered': [2]}, 'quality': {'next': 1, 'total': 0, 'trail': [], 'buffered': [2]}}, 'retained': [1, 2], 'acks': [[2, 'mes'], [2, 'quality']], 'commands': 2}
    assert request == before

def test_stale_worker_cannot_compact():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 1}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'deliver', 'seq': 1, 'consumer': 'quality', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'acquire', 'owner': 'w', 'now': 1, 'ttl': 100}, {'op': 'compact', 'owner': 'w', 'token': 1, 'now': 1, 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 1, 'acked', 'acked', 2, 'fenced'], 'next_sequence': 2, 'total': 5, 'epoch': 2, 'compacted': 0, 'lease': ['w', 2, 101], 'consumers': {'mes': {'next': 2, 'total': 5, 'trail': ['e1'], 'buffered': []}, 'quality': {'next': 2, 'total': 5, 'trail': ['e1'], 'buffered': []}}, 'retained': [1], 'acks': [[1, 'mes'], [1, 'quality']], 'commands': 1}
    assert request == before

def test_missing_payload_after_compaction():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 100}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'deliver', 'seq': 1, 'consumer': 'quality', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'compact', 'owner': 'w', 'token': 1, 'now': 0, 'crash': False}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 1, 'acked', 'acked', 1, 'missing'], 'next_sequence': 2, 'total': 5, 'epoch': 1, 'compacted': 1, 'lease': ['w', 1, 100], 'consumers': {'mes': {'next': 2, 'total': 5, 'trail': ['e1'], 'buffered': []}, 'quality': {'next': 2, 'total': 5, 'trail': ['e1'], 'buffered': []}}, 'retained': [], 'acks': [], 'commands': 1}
    assert request == before

def test_lease_after_empty_retirement():
    request = {'commands': [{'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 100}, {'op': 'retire', 'owner': 'w', 'token': 1, 'now': 0}, {'op': 'restart'}, {'op': 'acquire', 'owner': 'other', 'now': 1, 'ttl': 100}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 'retired', 'restarted', 2], 'next_sequence': 1, 'total': 0, 'epoch': 2, 'compacted': 0, 'lease': ['other', 2, 101], 'consumers': {'mes': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}, 'quality': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}}, 'retained': [], 'acks': [], 'commands': 0}
    assert request == before

