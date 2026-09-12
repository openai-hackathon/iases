import copy
import pytest
from fabops.domain import run


def test_normal():
    request = {'timeouts': [30]}
    before = copy.deepcopy(request)
    assert run(request) == [True]
    assert request == before

def test_null():
    request = {'timeouts': [None]}
    before = copy.deepcopy(request)
    assert run(request) == [False]
    assert request == before

def test_boolean():
    request = {'timeouts': [True]}
    before = copy.deepcopy(request)
    assert run(request) == [False]
    assert request == before

def test_text():
    request = {'timeouts': ['30']}
    before = copy.deepcopy(request)
    assert run(request) == [False]
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
