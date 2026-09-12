import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'capacity': 4, 'lots': []}
    before = copy.deepcopy(request)
    assert run(request) == []
    assert request == before

def test_single():
    request = {'capacity': 4, 'lots': [{'id': '0', 'product': 'p', 'recipe': 'r', 'reticle': 't', 'units': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == [['0']]
    assert request == before

def test_reticles():
    request = {'capacity': 4, 'lots': [{'id': '0', 'product': 'p', 'recipe': 'r', 'reticle': 'a', 'units': 1}, {'id': '1', 'product': 'p', 'recipe': 'r', 'reticle': 'b', 'units': 1}]}
    before = copy.deepcopy(request)
    assert run(request) == [['0'], ['1']]
    assert request == before

def test_combine():
    request = {'capacity': 4, 'lots': [{'id': '0', 'product': 'p', 'recipe': 'r', 'reticle': 't', 'units': 2}, {'id': '1', 'product': 'p', 'recipe': 'r', 'reticle': 't', 'units': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == [['0', '1']]
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
