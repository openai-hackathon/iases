import copy
import pytest
from fabops.domain import run


def test_same():
    request = {'start': 'a', 'end': 'a', 'edges': []}
    before = copy.deepcopy(request)
    assert run(request) == 0
    assert request == before

def test_direct():
    request = {'start': 'a', 'end': 'b', 'edges': [['a', 'b', 4]]}
    before = copy.deepcopy(request)
    assert run(request) == 4
    assert request == before

def test_reverse():
    request = {'start': 'b', 'end': 'a', 'edges': [['a', 'b', 4]]}
    before = copy.deepcopy(request)
    assert run(request) == None
    assert request == before

def test_missing():
    request = {'start': 'a', 'end': 'c', 'edges': []}
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
