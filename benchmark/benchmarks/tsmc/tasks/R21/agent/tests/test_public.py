import copy
import pytest
from fabops.domain import run


def test_first_command():
    request = {'commands': [{'op': 'execute', 'key': 'k', 'expected': 0, 'value': 1, 'scope': ['fab', 'cell']}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'status': 'applied', 'revision': 1, 'value': 1}], 'states': [[['fab', 'cell'], 1, 1]], 'receipts': 1}
    assert request == before

def test_scope_separates_plants():
    request = {'commands': [{'op': 'execute', 'key': 'k', 'expected': 0, 'value': 1, 'scope': ['a', 'cell']}, {'op': 'execute', 'key': 'k', 'expected': 0, 'value': 2, 'scope': ['b', 'cell']}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'status': 'applied', 'revision': 1, 'value': 1}, {'status': 'applied', 'revision': 1, 'value': 2}], 'states': [[['a', 'cell'], 1, 1], [['b', 'cell'], 1, 2]], 'receipts': 2}
    assert request == before

def test_object_order_and_numeric_equivalence():
    request = {'commands': [{'op': 'execute', 'key': 'k', 'expected': 0, 'value': {'a': 1, 'b': [2, 3]}, 'scope': ['fab', 'cell']}, {'op': 'execute', 'key': 'k', 'expected': 0, 'value': {'b': [2.0, 3], 'a': 1.0}, 'scope': ['fab', 'cell']}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'status': 'applied', 'revision': 1, 'value': {'a': 1, 'b': [2, 3]}}, {'status': 'applied', 'revision': 1, 'value': {'a': 1, 'b': [2, 3]}}], 'states': [[['fab', 'cell'], 1, {'a': 1, 'b': [2, 3]}]], 'receipts': 1}
    assert request == before

def test_crash_then_retry():
    request = {'commands': [{'op': 'execute', 'key': 'k', 'expected': 0, 'value': 1, 'scope': ['fab', 'cell'], 'crash': True}, {'op': 'restart'}, {'op': 'execute', 'key': 'k', 'expected': 0, 'value': 1, 'scope': ['fab', 'cell']}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [{'status': 'crashed'}, {'status': 'restarted'}, {'status': 'applied', 'revision': 1, 'value': 1}], 'states': [[['fab', 'cell'], 1, 1]], 'receipts': 1}
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
