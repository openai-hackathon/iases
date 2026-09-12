import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'jobs': []}
    before = copy.deepcopy(request)
    assert run(request) == {}
    assert request == before

def test_single():
    request = {'jobs': [{'id': 'a', 'resource': 'm', 'duration': 3, 'depends': [], 'release': 0}]}
    before = copy.deepcopy(request)
    assert run(request) == {'a': [0, 3]}
    assert request == before

def test_dependency():
    request = {'jobs': [{'id': 'a', 'resource': 'm', 'duration': 3, 'depends': [], 'release': 0}, {'id': 'b', 'resource': 'n', 'duration': 2, 'depends': ['a'], 'release': 0}]}
    before = copy.deepcopy(request)
    assert run(request) == {'a': [0, 3], 'b': [3, 5]}
    assert request == before

def test_parallel():
    request = {'jobs': [{'id': 'a', 'resource': 'm', 'duration': 3, 'depends': [], 'release': 0}, {'id': 'b', 'resource': 'n', 'duration': 2, 'depends': [], 'release': 0}]}
    before = copy.deepcopy(request)
    assert run(request) == {'a': [0, 3], 'b': [0, 2]}
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
