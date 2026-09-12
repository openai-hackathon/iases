import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'roles': ['qa', 'eng'], 'events': []}
    before = copy.deepcopy(request)
    assert run(request) == {'activations': [], 'active': None}
    assert request == before

def test_no_revision():
    request = {'roles': ['qa', 'eng'], 'events': [{'op': 'activate'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'activations': [False], 'active': None}
    assert request == before

def test_edit_clears():
    request = {'roles': ['qa', 'eng'], 'events': [{'op': 'edit', 'revision': 1}, {'op': 'approve', 'revision': 1, 'role': 'qa'}, {'op': 'approve', 'revision': 1, 'role': 'eng'}, {'op': 'edit', 'revision': 2}, {'op': 'activate'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'activations': [False], 'active': None}
    assert request == before

def test_partial():
    request = {'roles': ['qa', 'eng'], 'events': [{'op': 'edit', 'revision': 1}, {'op': 'approve', 'revision': 1, 'role': 'qa'}, {'op': 'activate'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'activations': [False], 'active': None}
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
