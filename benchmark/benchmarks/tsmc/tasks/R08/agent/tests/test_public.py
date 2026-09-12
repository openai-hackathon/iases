import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'entries': [], 'queries': []}
    before = copy.deepcopy(request)
    assert run(request) == []
    assert request == before

def test_single():
    request = {'entries': [{'tenant': 'a', 'key': 'x', 'value': 1}], 'queries': [{'tenant': 'a', 'key': 'x'}]}
    before = copy.deepcopy(request)
    assert run(request) == [1]
    assert request == before

def test_collision():
    request = {'entries': [{'tenant': 'a:b', 'key': 'c', 'value': 1}, {'tenant': 'a', 'key': 'b:c', 'value': 2}], 'queries': [{'tenant': 'a:b', 'key': 'c'}, {'tenant': 'a', 'key': 'b:c'}]}
    before = copy.deepcopy(request)
    assert run(request) == [1, 2]
    assert request == before

def test_missing():
    request = {'entries': [], 'queries': [{'tenant': 'a', 'key': 'x'}]}
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
