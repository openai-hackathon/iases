import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'values': [], 'q': 0.5}
    before = copy.deepcopy(request)
    assert run(request) == None
    assert request == before

def test_single():
    request = {'values': [5], 'q': 0.8}
    before = copy.deepcopy(request)
    assert run(request) == 5
    assert request == before

def test_even_median():
    request = {'values': [4, 1, 3, 2], 'q': 0.5}
    before = copy.deepcopy(request)
    assert run(request) == 2
    assert request == before

def test_minimum():
    request = {'values': [2, 1], 'q': 0}
    before = copy.deepcopy(request)
    assert run(request) == 1
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
