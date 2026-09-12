import copy
import pytest
from fabops.domain import run


def test_empty_batch():
    request = {'responses': []}
    before = copy.deepcopy(request)
    assert run(request) == []
    assert request == before

def test_unchanged_empty():
    request = {'responses': [{'nextSequence': 5, 'observations': []}]}
    before = copy.deepcopy(request)
    assert run(request) == [5]
    assert request == before

def test_normal():
    request = {'responses': [{'nextSequence': 4, 'observations': [1, 2, 3]}]}
    before = copy.deepcopy(request)
    assert run(request) == [4]
    assert request == before

def test_filtered():
    request = {'responses': [{'nextSequence': 10, 'observations': [3, 7]}]}
    before = copy.deepcopy(request)
    assert run(request) == [10]
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
