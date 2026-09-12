import copy
import pytest
from fabops.domain import run


def test_day():
    request = {'start': 480, 'end': 960, 'minutes': [479, 480, 959, 960]}
    before = copy.deepcopy(request)
    assert run(request) == [False, True, True, False]
    assert request == before

def test_night():
    request = {'start': 1320, 'end': 360, 'minutes': [0, 359, 360, 1319, 1320]}
    before = copy.deepcopy(request)
    assert run(request) == [True, True, False, False, True]
    assert request == before

def test_empty():
    request = {'start': 0, 'end': 0, 'minutes': [0, 1]}
    before = copy.deepcopy(request)
    assert run(request) == [False, False]
    assert request == before

def test_no_queries():
    request = {'start': 10, 'end': 20, 'minutes': []}
    before = copy.deepcopy(request)
    assert run(request) == []
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
