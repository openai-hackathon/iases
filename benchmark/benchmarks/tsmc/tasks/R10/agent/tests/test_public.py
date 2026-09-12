import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'cursor': 0, 'acks': []}
    before = copy.deepcopy(request)
    assert run(request) == 0
    assert request == before

def test_contiguous():
    request = {'cursor': 0, 'acks': [1, 2, 3]}
    before = copy.deepcopy(request)
    assert run(request) == 3
    assert request == before

def test_gap():
    request = {'cursor': 0, 'acks': [1, 3]}
    before = copy.deepcopy(request)
    assert run(request) == 1
    assert request == before

def test_duplicates():
    request = {'cursor': 0, 'acks': [1, 1]}
    before = copy.deepcopy(request)
    assert run(request) == 1
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
