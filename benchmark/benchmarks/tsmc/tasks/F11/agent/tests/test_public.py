import copy
import pytest
from fabops.domain import run


def test_control():
    request = {'horizon': [0, 20], 'open': [[0, 20]], 'maintenance': [], 'jobs': [], 'capacity': 2, 'query': {'ready': 0, 'duration': 4, 'units': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'profile': [[0, 20, 2]], 'available_unit_minutes': 40, 'booking': [0, 4]}
    assert request == before

def test_closures_cannot_be_compressed():
    request = {'horizon': [0, 20], 'open': [[0, 20]], 'maintenance': [[3, 8]], 'jobs': [], 'capacity': 2, 'query': {'ready': 0, 'duration': 6, 'units': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'profile': [[0, 3, 2], [3, 8, 0], [8, 20, 2]], 'available_unit_minutes': 30, 'booking': [8, 14]}
    assert request == before

def test_weighted_peak():
    request = {'horizon': [0, 20], 'open': [[0, 20]], 'maintenance': [], 'jobs': [{'start': 4, 'end': 12, 'units': 2}, {'start': 8, 'end': 16, 'units': 2}], 'capacity': 3, 'query': {'ready': 0, 'duration': 4, 'units': 3}}
    before = copy.deepcopy(request)
    assert run(request) == {'profile': [[0, 4, 3], [4, 8, 1], [8, 12, 0], [12, 16, 1], [16, 20, 3]], 'available_unit_minutes': 32, 'booking': [0, 4]}
    assert request == before

def test_capacity_change_is_continuous():
    request = {'horizon': [0, 20], 'open': [[0, 20]], 'maintenance': [], 'jobs': [{'start': 3, 'end': 9, 'units': 1}], 'capacity': 2, 'query': {'ready': 0, 'duration': 8, 'units': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'profile': [[0, 3, 2], [3, 9, 1], [9, 20, 2]], 'available_unit_minutes': 34, 'booking': [0, 8]}
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
