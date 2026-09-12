import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'records': [], 'consumers': []}
    before = copy.deepcopy(request)
    assert run(request) == []
    assert request == before

def test_one():
    request = {'records': [{'id': '0', 'offset': 0}, {'id': '1', 'offset': 1}, {'id': '2', 'offset': 2}], 'consumers': [{'active': True, 'ack': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == ['2']
    assert request == before

def test_slow():
    request = {'records': [{'id': '0', 'offset': 0}, {'id': '1', 'offset': 1}, {'id': '2', 'offset': 2}], 'consumers': [{'active': True, 'ack': 0}, {'active': True, 'ack': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == ['1', '2']
    assert request == before

def test_no_consumers():
    request = {'records': [{'id': '0', 'offset': 0}, {'id': '1', 'offset': 1}], 'consumers': []}
    before = copy.deepcopy(request)
    assert run(request) == ['0', '1']
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
