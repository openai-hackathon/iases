import copy
import pytest
from fabops.domain import run


def test_perfect():
    request = {'planned': 8, 'runtime': 8, 'lots': [{'total': 4, 'good': 4, 'ideal_cycle': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == {'availability': 1.0, 'performance': 1.0, 'quality': 1.0, 'oee': 1.0}
    assert request == before

def test_downtime():
    request = {'planned': 16, 'runtime': 8, 'lots': [{'total': 4, 'good': 4, 'ideal_cycle': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == {'availability': 0.5, 'performance': 1.0, 'quality': 1.0, 'oee': 0.5}
    assert request == before

def test_mixed():
    request = {'planned': 16, 'runtime': 8, 'lots': [{'total': 2, 'good': 2, 'ideal_cycle': 1}, {'total': 2, 'good': 2, 'ideal_cycle': 3}]}
    before = copy.deepcopy(request)
    assert run(request) == {'availability': 0.5, 'performance': 1.0, 'quality': 1.0, 'oee': 0.5}
    assert request == before

def test_quality():
    request = {'planned': 8, 'runtime': 8, 'lots': [{'total': 4, 'good': 2, 'ideal_cycle': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == {'availability': 1.0, 'performance': 1.0, 'quality': 0.5, 'oee': 0.5}
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
