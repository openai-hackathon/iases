import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'product': 'p', 'machine': 'm', 'rules': []}
    before = copy.deepcopy(request)
    assert run(request) == None
    assert request == before

def test_single():
    request = {'product': 'p', 'machine': 'm', 'rules': [{'id': 'a', 'product': 'p', 'machine': 'm', 'revision': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == 'a'
    assert request == before

def test_specific():
    request = {'product': 'p', 'machine': 'm', 'rules': [{'id': 'a', 'product': 'p', 'machine': 'm', 'revision': 1}, {'id': 'b', 'product': '*', 'machine': '*', 'revision': 9}]}
    before = copy.deepcopy(request)
    assert run(request) == 'a'
    assert request == before

def test_unmatched():
    request = {'product': 'p', 'machine': 'm', 'rules': [{'id': 'a', 'product': 'q', 'machine': 'm', 'revision': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == None
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
