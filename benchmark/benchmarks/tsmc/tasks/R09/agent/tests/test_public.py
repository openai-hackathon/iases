import copy
import pytest
from fabops.domain import run


def test_normal():
    request = {'mono_start': 0, 'mono_end': 2, 'wall_start': 100, 'wall_end': 102}
    before = copy.deepcopy(request)
    assert run(request) == 2
    assert request == before

def test_zero():
    request = {'mono_start': 1, 'mono_end': 1, 'wall_start': 100, 'wall_end': 100}
    before = copy.deepcopy(request)
    assert run(request) == 0
    assert request == before

def test_backward_jump():
    request = {'mono_start': 1, 'mono_end': 3, 'wall_start': 100, 'wall_end': 90}
    before = copy.deepcopy(request)
    assert run(request) == 2
    assert request == before

def test_forward_jump():
    request = {'mono_start': 1, 'mono_end': 3, 'wall_start': 100, 'wall_end': 200}
    before = copy.deepcopy(request)
    assert run(request) == 2
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
