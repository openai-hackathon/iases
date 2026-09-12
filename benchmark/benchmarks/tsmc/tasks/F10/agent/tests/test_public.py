import copy
import pytest
from fabops.domain import run


def test_safe():
    request = {'required': ['door'], 'observations': {'door': True}}
    before = copy.deepcopy(request)
    assert run(request) == True
    assert request == before

def test_unsafe():
    request = {'required': ['door'], 'observations': {'door': False}}
    before = copy.deepcopy(request)
    assert run(request) == False
    assert request == before

def test_missing():
    request = {'required': ['door'], 'observations': {}}
    before = copy.deepcopy(request)
    assert run(request) == False
    assert request == before

def test_empty():
    request = {'required': [], 'observations': {}}
    before = copy.deepcopy(request)
    assert run(request) == True
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
