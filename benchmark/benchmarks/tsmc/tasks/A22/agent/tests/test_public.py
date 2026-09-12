import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'measurements': []}
    before = copy.deepcopy(request)
    assert run(request) == []
    assert request == before

def test_pascal():
    request = {'measurements': [{'unit': 'Pa', 'value': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == [2]
    assert request == before

def test_bar():
    request = {'measurements': [{'unit': 'bar', 'value': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == [200000]
    assert request == before

def test_kilopascal():
    request = {'measurements': [{'unit': 'kPa', 'value': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == [2000]
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
