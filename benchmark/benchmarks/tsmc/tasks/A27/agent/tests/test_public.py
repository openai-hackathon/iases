import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'changes': []}
    before = copy.deepcopy(request)
    assert run(request) == []
    assert request == before

def test_one():
    request = {'changes': [{'effective': 1, 'value': 'a'}]}
    before = copy.deepcopy(request)
    assert run(request) == [{'start': 1, 'end': None, 'value': 'a'}]
    assert request == before

def test_late():
    request = {'changes': [{'effective': 1, 'value': 'a'}, {'effective': 5, 'value': 'c'}, {'effective': 3, 'value': 'b'}]}
    before = copy.deepcopy(request)
    assert run(request) == [{'start': 1, 'end': 3, 'value': 'a'}, {'start': 3, 'end': 5, 'value': 'b'}, {'start': 5, 'end': None, 'value': 'c'}]
    assert request == before

def test_ordered():
    request = {'changes': [{'effective': 1, 'value': 'a'}, {'effective': 3, 'value': 'b'}]}
    before = copy.deepcopy(request)
    assert run(request) == [{'start': 1, 'end': 3, 'value': 'a'}, {'start': 3, 'end': None, 'value': 'b'}]
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
