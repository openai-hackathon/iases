import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'records': []}
    before = copy.deepcopy(request)
    assert run(request) == {}
    assert request == before

def test_one():
    request = {'records': [{'key': 'a', 'version': 1, 'value': 2, 'deleted': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'a': 2}
    assert request == before

def test_delete():
    request = {'records': [{'key': 'a', 'version': 1, 'value': 2, 'deleted': False}, {'key': 'a', 'version': 2, 'value': None, 'deleted': True}]}
    before = copy.deepcopy(request)
    assert run(request) == {}
    assert request == before

def test_update():
    request = {'records': [{'key': 'a', 'version': 1, 'value': 2, 'deleted': False}, {'key': 'a', 'version': 2, 'value': 3, 'deleted': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'a': 3}
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
