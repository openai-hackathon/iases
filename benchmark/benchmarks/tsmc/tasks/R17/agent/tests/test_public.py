import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'capacity': 1, 'rate': 1, 'times': []}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [], 'milli_tokens': 1000}
    assert request == before

def test_initial():
    request = {'capacity': 1, 'rate': 1, 'times': [0]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True], 'milli_tokens': 0}
    assert request == before

def test_fraction():
    request = {'capacity': 1, 'rate': 1, 'times': [0, 500]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True, False], 'milli_tokens': 500}
    assert request == before

def test_full_second():
    request = {'capacity': 1, 'rate': 1, 'times': [0, 1000]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True, True], 'milli_tokens': 0}
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
