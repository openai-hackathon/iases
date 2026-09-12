import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'commands': []}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [], 'pending': [], 'projections': {'vds': {}, 'qdr': {}, 'tdp': {}}, 'receipts': 0}
    assert request == before

def test_one_complete():
    request = {'commands': [{'op': 'enqueue', 'event': {'id': 'e1', 'artifact': 'lot', 'revision': 1, 'payload': 'a'}, 'crash': False}, {'op': 'reconcile'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['queued', 'reconciled'], 'pending': [], 'projections': {'vds': {'lot': [1, 'a']}, 'qdr': {'lot': [1, 'a']}, 'tdp': {'lot': [1, 'a']}}, 'receipts': 3}
    assert request == before

def test_lost_ack_recovery():
    request = {'commands': [{'op': 'enqueue', 'event': {'id': 'e1', 'artifact': 'lot', 'revision': 1, 'payload': 'a'}, 'crash': False}, {'op': 'deliver', 'id': 'e1', 'channel': 'qdr', 'crash': 'after_sink'}, {'op': 'restart'}, {'op': 'reconcile'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['queued', 'crashed', 'restarted', 'reconciled'], 'pending': [], 'projections': {'vds': {'lot': [1, 'a']}, 'qdr': {'lot': [1, 'a']}, 'tdp': {'lot': [1, 'a']}}, 'receipts': 3}
    assert request == before

def test_interrupted_intent():
    request = {'commands': [{'op': 'enqueue', 'event': {'id': 'e1', 'artifact': 'lot', 'revision': 1, 'payload': 'a'}, 'crash': True}, {'op': 'restart'}, {'op': 'reconcile'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['crashed', 'restarted', 'reconciled'], 'pending': [], 'projections': {'vds': {}, 'qdr': {}, 'tdp': {}}, 'receipts': 0}
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
