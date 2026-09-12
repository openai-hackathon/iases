import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'events': []}
    before = copy.deepcopy(request)
    assert run(request) == {}
    assert request == before

def test_one():
    request = {'events': [{'lot': 'a', 'source': 'qa', 'version': 1, 'op': 'hold'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'a': ['qa']}
    assert request == before

def test_two_sources():
    request = {'events': [{'lot': 'a', 'source': 'qa', 'version': 1, 'op': 'hold'}, {'lot': 'a', 'source': 'eng', 'version': 1, 'op': 'hold'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'a': ['eng', 'qa']}
    assert request == before

def test_release():
    request = {'events': [{'lot': 'a', 'source': 'qa', 'version': 1, 'op': 'hold'}, {'lot': 'a', 'source': 'qa', 'version': 2, 'op': 'release'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'a': []}
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
