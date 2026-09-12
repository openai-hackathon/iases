import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'points': [], 'turns': 1, 'dx': 0, 'dy': 0}
    before = copy.deepcopy(request)
    assert run(request) == []
    assert request == before

def test_identity():
    request = {'points': [[1, 2]], 'turns': 0, 'dx': 0, 'dy': 0}
    before = copy.deepcopy(request)
    assert run(request) == [[1, 2]]
    assert request == before

def test_quarter():
    request = {'points': [[1, 2]], 'turns': 1, 'dx': 0, 'dy': 0}
    before = copy.deepcopy(request)
    assert run(request) == [[-2, 1]]
    assert request == before

def test_half():
    request = {'points': [[1, 2]], 'turns': 2, 'dx': 0, 'dy': 0}
    before = copy.deepcopy(request)
    assert run(request) == [[-1, -2]]
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
