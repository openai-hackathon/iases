import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'gap': 2, 'times': []}
    before = copy.deepcopy(request)
    assert run(request) == []
    assert request == before

def test_one():
    request = {'gap': 2, 'times': [3]}
    before = copy.deepcopy(request)
    assert run(request) == [[3, 3, 1]]
    assert request == before

def test_late_bridge():
    request = {'gap': 3, 'times': [0, 6, 3]}
    before = copy.deepcopy(request)
    assert run(request) == [[0, 6, 3]]
    assert request == before

def test_separate():
    request = {'gap': 2, 'times': [0, 5]}
    before = copy.deepcopy(request)
    assert run(request) == [[0, 0, 1], [5, 5, 1]]
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
