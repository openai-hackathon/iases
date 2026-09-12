import copy
import pytest
from fabops.domain import run


def test_quantity_0_capacity_25():
    request = {'quantity': 0, 'capacity': 25}
    before = copy.deepcopy(request)
    assert run(request) == 0
    assert request == before

def test_quantity_25_capacity_25():
    request = {'quantity': 25, 'capacity': 25}
    before = copy.deepcopy(request)
    assert run(request) == 1
    assert request == before

def test_quantity_26_capacity_25():
    request = {'quantity': 26, 'capacity': 25}
    before = copy.deepcopy(request)
    assert run(request) == 2
    assert request == before

def test_quantity_50_capacity_25():
    request = {'quantity': 50, 'capacity': 25}
    before = copy.deepcopy(request)
    assert run(request) == 2
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
