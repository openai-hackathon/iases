import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'samples': []}
    before = copy.deepcopy(request)
    assert run(request) == 0
    assert request == before

def test_single():
    request = {'samples': [[1, 8]]}
    before = copy.deepcopy(request)
    assert run(request) == 0
    assert request == before

def test_reset():
    request = {'samples': [[1, 9], [2, 2]]}
    before = copy.deepcopy(request)
    assert run(request) == 2
    assert request == before

def test_increase():
    request = {'samples': [[1, 2], [2, 5]]}
    before = copy.deepcopy(request)
    assert run(request) == 3
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
