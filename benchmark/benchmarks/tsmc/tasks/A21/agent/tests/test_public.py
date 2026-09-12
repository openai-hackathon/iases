import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'rows': [], 'cursor': None, 'limit': 2}
    before = copy.deepcopy(request)
    assert run(request) == {'rows': [], 'next_cursor': None}
    assert request == before

def test_one():
    request = {'rows': [{'time': 1, 'id': 'a', 'value': 'a'}], 'cursor': None, 'limit': 2}
    before = copy.deepcopy(request)
    assert run(request) == {'rows': [{'time': 1, 'id': 'a', 'value': 'a'}], 'next_cursor': [1, 'a']}
    assert request == before

def test_same_time():
    request = {'rows': [{'time': 1, 'id': 'a', 'value': 'a'}, {'time': 1, 'id': 'b', 'value': 'b'}], 'cursor': [1, 'a'], 'limit': 2}
    before = copy.deepcopy(request)
    assert run(request) == {'rows': [{'time': 1, 'id': 'b', 'value': 'b'}], 'next_cursor': [1, 'b']}
    assert request == before

def test_later():
    request = {'rows': [{'time': 1, 'id': 'a', 'value': 'a'}, {'time': 2, 'id': 'b', 'value': 'b'}], 'cursor': [1, 'a'], 'limit': 2}
    before = copy.deepcopy(request)
    assert run(request) == {'rows': [{'time': 2, 'id': 'b', 'value': 'b'}], 'next_cursor': [2, 'b']}
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
