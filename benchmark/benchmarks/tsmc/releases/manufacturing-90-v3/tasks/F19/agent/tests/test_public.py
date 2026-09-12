import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'lots': [], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'observed': {'dispatch': 1, 'inventory': 1}, 'current': {'dispatch': 1, 'inventory': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [], 'committed': True, 'stock': {'r': 1, 's': 1}}
    assert request == before

def test_one():
    request = {'lots': [{'id': 'a', 'priority': 1, 'reticle': 'r', 'costs': {'x': 1}}], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'observed': {'dispatch': 1, 'inventory': 1}, 'current': {'dispatch': 1, 'inventory': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [['a', 'x']], 'committed': True, 'stock': {'r': 0, 's': 1}}
    assert request == before

def test_cardinality():
    request = {'lots': [{'id': 'a', 'priority': 9, 'reticle': 'r', 'costs': {'x': 0}}, {'id': 'b', 'priority': 1, 'reticle': 'r', 'costs': {'y': 0}}, {'id': 'c', 'priority': 1, 'reticle': 's', 'costs': {'x': 0}}], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'observed': {'dispatch': 1, 'inventory': 1}, 'current': {'dispatch': 1, 'inventory': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [['b', 'y'], ['c', 'x']], 'committed': True, 'stock': {'r': 0, 's': 0}}
    assert request == before

def test_no_eligible_tool():
    request = {'lots': [{'id': 'a', 'priority': 1, 'reticle': 'r', 'costs': {'z': 1}}], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'observed': {'dispatch': 1, 'inventory': 1}, 'current': {'dispatch': 1, 'inventory': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [], 'committed': True, 'stock': {'r': 1, 's': 1}}
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
