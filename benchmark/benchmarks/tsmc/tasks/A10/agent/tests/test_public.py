import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'values': []}
    before = copy.deepcopy(request)
    assert run(request) == '0.00'
    assert request == before

def test_whole():
    request = {'values': ['2', '3']}
    before = copy.deepcopy(request)
    assert run(request) == '5.00'
    assert request == before

def test_sum_before_round():
    request = {'values': ['0.004', '0.004']}
    before = copy.deepcopy(request)
    assert run(request) == '0.01'
    assert request == before

def test_single_tie():
    request = {'values': ['1.005']}
    before = copy.deepcopy(request)
    assert run(request) == '1.01'
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
