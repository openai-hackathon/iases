import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'messages': [], 'max_attempts': 2}
    before = copy.deepcopy(request)
    assert run(request) == {'processed': [], 'dead_letter': [], 'attempts': {}}
    assert request == before

def test_valid():
    request = {'messages': [{'id': '0', 'valid': True}], 'max_attempts': 2}
    before = copy.deepcopy(request)
    assert run(request) == {'processed': ['0'], 'dead_letter': [], 'attempts': {'0': 1}}
    assert request == before

def test_poison_first():
    request = {'messages': [{'id': '0', 'valid': False}, {'id': '1', 'valid': True}], 'max_attempts': 2}
    before = copy.deepcopy(request)
    assert run(request) == {'processed': ['1'], 'dead_letter': ['0'], 'attempts': {'0': 2, '1': 1}}
    assert request == before

def test_poison_only():
    request = {'messages': [{'id': '0', 'valid': False}], 'max_attempts': 2}
    before = copy.deepcopy(request)
    assert run(request) == {'processed': [], 'dead_letter': ['0'], 'attempts': {'0': 2}}
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
