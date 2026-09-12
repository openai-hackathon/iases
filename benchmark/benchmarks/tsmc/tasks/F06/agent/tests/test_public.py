import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'versions': []}
    before = copy.deepcopy(request)
    assert run(request) == None
    assert request == before

def test_single():
    request = {'versions': ['1.0.0']}
    before = copy.deepcopy(request)
    assert run(request) == '1.0.0'
    assert request == before

def test_major_numeric():
    request = {'versions': ['2.0.0', '10.0.0']}
    before = copy.deepcopy(request)
    assert run(request) == '10.0.0'
    assert request == before

def test_normal():
    request = {'versions': ['1.0.0', '2.0.0']}
    before = copy.deepcopy(request)
    assert run(request) == '2.0.0'
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
