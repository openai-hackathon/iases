import copy
import pytest
from fabops.domain import run


def test_seconds():
    request = {'header': '15', 'now': 'Wed, 01 Jan 2025 00:00:00 GMT'}
    before = copy.deepcopy(request)
    assert run(request) == 15
    assert request == before

def test_zero():
    request = {'header': '0', 'now': 'Wed, 01 Jan 2025 00:00:00 GMT'}
    before = copy.deepcopy(request)
    assert run(request) == 0
    assert request == before

def test_date():
    request = {'header': 'Wed, 01 Jan 2025 00:00:05 GMT', 'now': 'Wed, 01 Jan 2025 00:00:00 GMT'}
    before = copy.deepcopy(request)
    assert run(request) == 5
    assert request == before

def test_malformed():
    request = {'header': 'later', 'now': 'Wed, 01 Jan 2025 00:00:00 GMT'}
    before = copy.deepcopy(request)
    assert run(request) == None
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
