import copy
import pytest
from fabops.domain import run


def test_start():
    request = {'route': ['wash', 'coat'], 'completed': 0}
    before = copy.deepcopy(request)
    assert run(request) == 'wash'
    assert request == before

def test_advance():
    request = {'route': ['wash', 'coat'], 'completed': 1}
    before = copy.deepcopy(request)
    assert run(request) == 'coat'
    assert request == before

def test_rework_occurrence():
    request = {'route': ['wash', 'coat', 'wash', 'inspect'], 'completed': 3}
    before = copy.deepcopy(request)
    assert run(request) == 'inspect'
    assert request == before

def test_empty():
    request = {'route': [], 'completed': 0}
    before = copy.deepcopy(request)
    assert run(request) == None
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
