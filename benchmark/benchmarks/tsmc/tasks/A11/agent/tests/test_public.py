import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'samples': []}
    before = copy.deepcopy(request)
    assert run(request) == 0
    assert request == before

def test_single():
    request = {'samples': [[0, 4]]}
    before = copy.deepcopy(request)
    assert run(request) == 0
    assert request == before

def test_ramp():
    request = {'samples': [[0, 0], [2, 4]]}
    before = copy.deepcopy(request)
    assert run(request) == 4
    assert request == before

def test_flat():
    request = {'samples': [[0, 3], [4, 3]]}
    before = copy.deepcopy(request)
    assert run(request) == 12
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
