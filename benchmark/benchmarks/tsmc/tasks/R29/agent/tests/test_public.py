import copy
import pytest
from fabops.domain import run


def test_ordered_two_consumers():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 100}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'deliver', 'seq': 1, 'consumer': 'quality', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 1, 'acked', 'acked'], 'next_sequence': 2, 'total': 5, 'epoch': 1, 'compacted': 0, 'lease': ['w', 1, 100], 'consumers': {'mes': {'next': 2, 'total': 5, 'trail': ['e1'], 'buffered': []}, 'quality': {'next': 2, 'total': 5, 'trail': ['e1'], 'buffered': []}}, 'retained': [1], 'acks': [[1, 'mes'], [1, 'quality']], 'commands': 1}
    assert request == before

def test_consumer_gap_survives_restart():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'append', 'id': 'e2', 'delta': 7, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 100}, {'op': 'deliver', 'seq': 2, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'restart'}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 2, 1, 'acked', 'restarted', 'acked'], 'next_sequence': 3, 'total': 12, 'epoch': 1, 'compacted': 0, 'lease': ['w', 1, 100], 'consumers': {'mes': {'next': 3, 'total': 12, 'trail': ['e1', 'e2'], 'buffered': []}, 'quality': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}}, 'retained': [1, 2], 'acks': [[1, 'mes'], [2, 'mes']], 'commands': 2}
    assert request == before

def test_lost_ack_retries_without_duplicate_effect():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 100}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'after_sink'}, {'op': 'restart'}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 1, 'crashed', 'restarted', 'acked'], 'next_sequence': 2, 'total': 5, 'epoch': 1, 'compacted': 0, 'lease': ['w', 1, 100], 'consumers': {'mes': {'next': 2, 'total': 5, 'trail': ['e1'], 'buffered': []}, 'quality': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}}, 'retained': [1], 'acks': [[1, 'mes']], 'commands': 1}
    assert request == before

def test_compaction_waits_for_other_consumer():
    request = {'commands': [{'op': 'append', 'id': 'e1', 'delta': 5, 'crash': False}, {'op': 'acquire', 'owner': 'w', 'now': 0, 'ttl': 100}, {'op': 'deliver', 'seq': 1, 'consumer': 'mes', 'owner': 'w', 'token': 1, 'now': 0, 'crash': 'none'}, {'op': 'compact', 'owner': 'w', 'token': 1, 'now': 0, 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [1, 1, 'acked', 0], 'next_sequence': 2, 'total': 5, 'epoch': 1, 'compacted': 0, 'lease': ['w', 1, 100], 'consumers': {'mes': {'next': 2, 'total': 5, 'trail': ['e1'], 'buffered': []}, 'quality': {'next': 1, 'total': 0, 'trail': [], 'buffered': []}}, 'retained': [1], 'acks': [[1, 'mes']], 'commands': 1}
    assert request == before


def test_public_cli_fixture():
    import json
    from pathlib import Path
    import subprocess
    import sys
    completed = subprocess.run(
        [sys.executable, "-m", "fabops", "--input", "data/request.json"],
        capture_output=True, text=True, timeout=10, check=True)
    assert json.loads(completed.stdout) == json.loads(Path("data/expected.json").read_text())
