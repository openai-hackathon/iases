import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'values': [], 'fail': False, 'retry': False}
    before = copy.deepcopy(request)
    assert run(request) == {'columns': ['value', 'unit'], 'rows': []}
    assert request == before

def test_success():
    request = {'values': [1, 2], 'fail': False, 'retry': False}
    before = copy.deepcopy(request)
    assert run(request) == {'columns': ['value', 'unit'], 'rows': [[1, 'Pa'], [2, 'Pa']]}
    assert request == before

def test_rollback():
    request = {'values': [1], 'fail': True, 'retry': False}
    before = copy.deepcopy(request)
    assert run(request) == {'columns': ['value'], 'rows': [[1]]}
    assert request == before

def test_zero():
    request = {'values': [0], 'fail': False, 'retry': False}
    before = copy.deepcopy(request)
    assert run(request) == {'columns': ['value', 'unit'], 'rows': [[0, 'Pa']]}
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
