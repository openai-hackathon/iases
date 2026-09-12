import copy
import pytest
from fabops.domain import run


def test_inside():
    request = {'at': '2025-01-01T01:00+00:00', 'qualifications': [{'id': 'q', 'start': '2025-01-01T00:00+00:00', 'end': '2025-01-01T02:00+00:00'}]}
    before = copy.deepcopy(request)
    assert run(request) == ['q']
    assert request == before

def test_outside():
    request = {'at': '2025-01-01T03:00+00:00', 'qualifications': [{'id': 'q', 'start': '2025-01-01T00:00+00:00', 'end': '2025-01-01T02:00+00:00'}]}
    before = copy.deepcopy(request)
    assert run(request) == []
    assert request == before

def test_offset():
    request = {'at': '2025-01-01T09:00+08:00', 'qualifications': [{'id': 'q', 'start': '2025-01-01T00:00+00:00', 'end': '2025-01-01T02:00+00:00'}]}
    before = copy.deepcopy(request)
    assert run(request) == ['q']
    assert request == before

def test_start():
    request = {'at': '2025-01-01T00:00+00:00', 'qualifications': [{'id': 'q', 'start': '2025-01-01T00:00+00:00', 'end': '2025-01-01T02:00+00:00'}]}
    before = copy.deepcopy(request)
    assert run(request) == ['q']
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
