import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'parts': [], 'stations': ['s'], 'measurements': []}
    before = copy.deepcopy(request)
    assert run(request) == []
    assert request == before

def test_one():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'part': 'p', 'station': 's', 'value': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == [{'part': 'p', 'values': [2]}]
    assert request == before

def test_zero():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'part': 'p', 'station': 's', 'value': 0}]}
    before = copy.deepcopy(request)
    assert run(request) == [{'part': 'p', 'values': [0]}]
    assert request == before

def test_missing():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': []}
    before = copy.deepcopy(request)
    assert run(request) == [{'part': 'p', 'values': [None]}]
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
