import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'values': []}
    before = copy.deepcopy(request)
    assert run(request) == None
    assert request == before

def test_available():
    request = {'values': [1, 3]}
    before = copy.deepcopy(request)
    assert run(request) == 2.0
    assert request == before

def test_missing():
    request = {'values': [2, None]}
    before = copy.deepcopy(request)
    assert run(request) == 2.0
    assert request == before

def test_zero():
    request = {'values': [0, 4]}
    before = copy.deepcopy(request)
    assert run(request) == 2.0
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
