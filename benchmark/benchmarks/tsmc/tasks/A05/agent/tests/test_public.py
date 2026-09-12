import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'lots': []}
    before = copy.deepcopy(request)
    assert run(request) == None
    assert request == before

def test_single():
    request = {'lots': [{'good': 1, 'tested': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == 0.5
    assert request == before

def test_unequal():
    request = {'lots': [{'good': 1, 'tested': 1}, {'good': 0, 'tested': 3}]}
    before = copy.deepcopy(request)
    assert run(request) == 0.25
    assert request == before

def test_equal_sizes():
    request = {'lots': [{'good': 2, 'tested': 2}, {'good': 0, 'tested': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == 0.5
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
