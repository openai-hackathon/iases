import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'stock': 5, 'balance': 10, 'orders': []}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [], 'stock': 5, 'balance': 10}
    assert request == before

def test_success():
    request = {'stock': 5, 'balance': 10, 'orders': [{'quantity': 2, 'price': 3, 'failure': 'none'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True], 'stock': 3, 'balance': 7}
    assert request == before

def test_charge_fails():
    request = {'stock': 5, 'balance': 10, 'orders': [{'quantity': 2, 'price': 3, 'failure': 'charge'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [False], 'stock': 5, 'balance': 10}
    assert request == before

def test_no_stock():
    request = {'stock': 1, 'balance': 10, 'orders': [{'quantity': 2, 'price': 3, 'failure': 'none'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [False], 'stock': 1, 'balance': 10}
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
