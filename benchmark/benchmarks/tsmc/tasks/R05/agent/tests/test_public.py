import copy
import pytest
from fabops.domain import run


def test_available():
    request = {'attempts': 0, 'max_attempts': 3, 'elapsed': 0, 'deadline': 10}
    before = copy.deepcopy(request)
    assert run(request) == True
    assert request == before

def test_all_exhausted():
    request = {'attempts': 3, 'max_attempts': 3, 'elapsed': 10, 'deadline': 10}
    before = copy.deepcopy(request)
    assert run(request) == False
    assert request == before

def test_attempts_exhausted():
    request = {'attempts': 3, 'max_attempts': 3, 'elapsed': 0, 'deadline': 10}
    before = copy.deepcopy(request)
    assert run(request) == False
    assert request == before

def test_time_exhausted():
    request = {'attempts': 0, 'max_attempts': 3, 'elapsed': 10, 'deadline': 10}
    before = copy.deepcopy(request)
    assert run(request) == False
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
