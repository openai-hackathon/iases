import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'labels': []}
    before = copy.deepcopy(request)
    assert run(request) == []
    assert request == before

def test_fail():
    request = {'labels': [1]}
    before = copy.deepcopy(request)
    assert run(request) == [True]
    assert request == before

def test_pass():
    request = {'labels': [-1]}
    before = copy.deepcopy(request)
    assert run(request) == [False]
    assert request == before

def test_mixed():
    request = {'labels': [-1, 1]}
    before = copy.deepcopy(request)
    assert run(request) == [False, True]
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
