import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'rows': []}
    before = copy.deepcopy(request)
    assert run(request) == {}
    assert request == before

def test_one():
    request = {'rows': [{'group': 'g', 'part': 'p', 'good': True}]}
    before = copy.deepcopy(request)
    assert run(request) == {'g': {'good': 1, 'total': 1}}
    assert request == before

def test_repeat():
    request = {'rows': [{'group': 'g', 'part': 'p', 'good': True}, {'group': 'g', 'part': 'p', 'good': True}]}
    before = copy.deepcopy(request)
    assert run(request) == {'g': {'good': 1, 'total': 1}}
    assert request == before

def test_two():
    request = {'rows': [{'group': 'g', 'part': 'p', 'good': True}, {'group': 'g', 'part': 'q', 'good': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'g': {'good': 1, 'total': 2}}
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
