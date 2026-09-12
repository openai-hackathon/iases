import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'start': 0, 'end': 6, 'priority': ['safety', 'maintenance'], 'intervals': []}
    before = copy.deepcopy(request)
    assert run(request) == {'safety': 0, 'maintenance': 0}
    assert request == before

def test_single():
    request = {'start': 0, 'end': 6, 'priority': ['safety', 'maintenance'], 'intervals': [{'cause': 'maintenance', 'start': 1, 'end': 3}]}
    before = copy.deepcopy(request)
    assert run(request) == {'safety': 0, 'maintenance': 2}
    assert request == before

def test_overlap():
    request = {'start': 0, 'end': 6, 'priority': ['safety', 'maintenance'], 'intervals': [{'cause': 'safety', 'start': 2, 'end': 4}, {'cause': 'maintenance', 'start': 1, 'end': 5}]}
    before = copy.deepcopy(request)
    assert run(request) == {'safety': 2, 'maintenance': 2}
    assert request == before

def test_disjoint():
    request = {'start': 0, 'end': 6, 'priority': ['safety', 'maintenance'], 'intervals': [{'cause': 'safety', 'start': 0, 'end': 2}, {'cause': 'maintenance', 'start': 3, 'end': 5}]}
    before = copy.deepcopy(request)
    assert run(request) == {'safety': 2, 'maintenance': 2}
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
