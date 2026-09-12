import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'orders': {}, 'receipts': [], 'invoices': []}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [], 'billed': {}}
    assert request == before

def test_one():
    request = {'orders': {'a': 5}, 'receipts': [{'line': 'a', 'quantity': 5}], 'invoices': [{'line': 'a', 'quantity': 3}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [True], 'billed': {'a': 3}}
    assert request == before

def test_cross_line():
    request = {'orders': {'a': 5, 'b': 5}, 'receipts': [{'line': 'b', 'quantity': 5}], 'invoices': [{'line': 'a', 'quantity': 3}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [False], 'billed': {'a': 0, 'b': 0}}
    assert request == before

def test_unknown():
    request = {'orders': {}, 'receipts': [], 'invoices': [{'line': 'a', 'quantity': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == {'accepted': [False], 'billed': {}}
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
