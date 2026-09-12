import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'calibrations': [], 'samples': []}
    before = copy.deepcopy(request)
    assert run(request) == []
    assert request == before

def test_exact():
    request = {'calibrations': [{'effective': 2, 'gain': 2, 'offset': 1}], 'samples': [[2, 3]]}
    before = copy.deepcopy(request)
    assert run(request) == [7]
    assert request == before

def test_after():
    request = {'calibrations': [{'effective': 2, 'gain': 2, 'offset': 1}], 'samples': [[3, 3]]}
    before = copy.deepcopy(request)
    assert run(request) == [7]
    assert request == before

def test_no_rules():
    request = {'calibrations': [], 'samples': [[1, 3]]}
    before = copy.deepcopy(request)
    assert run(request) == [None]
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
