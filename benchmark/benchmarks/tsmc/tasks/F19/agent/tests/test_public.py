import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'lots': [], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'horizon': 4, 'observed': {'dispatch': 1, 'calendar': 1}, 'current': {'dispatch': 1, 'calendar': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [], 'status': 'committed', 'reservations': []}
    assert request == before

def test_one():
    request = {'lots': [{'id': 'a', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0}, 'durations': {'x': 1}, 'release': 0, 'deadline': 4}], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'horizon': 4, 'observed': {'dispatch': 1, 'calendar': 1}, 'current': {'dispatch': 1, 'calendar': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [['a', 'x', 0, 1]], 'status': 'committed', 'reservations': [['a', 'x', 0, 1]]}
    assert request == before

def test_reusable_reticle():
    request = {'lots': [{'id': 'b', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0}, 'durations': {'x': 1}, 'release': 0, 'deadline': 4}, {'id': 'a', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0}, 'durations': {'x': 1}, 'release': 0, 'deadline': 4}], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'horizon': 4, 'observed': {'dispatch': 1, 'calendar': 1}, 'current': {'dispatch': 1, 'calendar': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [['a', 'x', 0, 1], ['b', 'x', 1, 2]], 'status': 'committed', 'reservations': [['a', 'x', 0, 1], ['b', 'x', 1, 2]]}
    assert request == before

def test_cooldown():
    request = {'lots': [{'id': 'a', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0}, 'durations': {'x': 1}, 'release': 0, 'deadline': 4, 'cooldown': 2}, {'id': 'b', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0}, 'durations': {'x': 1}, 'release': 0, 'deadline': 4}], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'horizon': 4, 'observed': {'dispatch': 1, 'calendar': 1}, 'current': {'dispatch': 1, 'calendar': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [['a', 'x', 1, 2], ['b', 'x', 0, 1]], 'status': 'committed', 'reservations': [['a', 'x', 1, 2], ['b', 'x', 0, 1]]}
    assert request == before

def test_later_id_precedes():
    request = {'lots': [{'id': 'a', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0}, 'durations': {'x': 1}, 'release': 0, 'deadline': 4, 'after': ['z']}, {'id': 'z', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0}, 'durations': {'x': 1}, 'release': 0, 'deadline': 4}], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'horizon': 4, 'observed': {'dispatch': 1, 'calendar': 1}, 'current': {'dispatch': 1, 'calendar': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [['a', 'x', 1, 2], ['z', 'x', 0, 1]], 'status': 'committed', 'reservations': [['a', 'x', 1, 2], ['z', 'x', 0, 1]]}
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
