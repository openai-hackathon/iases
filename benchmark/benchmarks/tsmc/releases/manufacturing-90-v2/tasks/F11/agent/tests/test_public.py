import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'start': 0, 'end': 10, 'maintenance': []}
    before = copy.deepcopy(request)
    assert run(request) == 10
    assert request == before

def test_single():
    request = {'start': 0, 'end': 10, 'maintenance': [[2, 4]]}
    before = copy.deepcopy(request)
    assert run(request) == 8
    assert request == before

def test_overlap():
    request = {'start': 0, 'end': 10, 'maintenance': [[2, 6], [4, 8]]}
    before = copy.deepcopy(request)
    assert run(request) == 4
    assert request == before

def test_touching():
    request = {'start': 0, 'end': 10, 'maintenance': [[2, 4], [4, 6]]}
    before = copy.deepcopy(request)
    assert run(request) == 6
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
