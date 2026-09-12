import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'ids': [], 'responses': []}
    before = copy.deepcopy(request)
    assert run(request) == []
    assert request == before

def test_one():
    request = {'ids': ['a'], 'responses': [{'id': 'a', 'value': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == [2]
    assert request == before

def test_reverse():
    request = {'ids': ['a', 'b'], 'responses': [{'id': 'b', 'value': 2}, {'id': 'a', 'value': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == [1, 2]
    assert request == before

def test_missing():
    request = {'ids': ['a'], 'responses': []}
    before = copy.deepcopy(request)
    assert run(request) == [None]
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
