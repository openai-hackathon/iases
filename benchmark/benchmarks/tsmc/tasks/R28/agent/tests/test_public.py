import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'lines': []}
    before = copy.deepcopy(request)
    assert run(request) == []
    assert request == before

def test_valid():
    request = {'lines': ['1|a|63d73181', '2|b|f898de62']}
    before = copy.deepcopy(request)
    assert run(request) == ['a', 'b']
    assert request == before

def test_interior_corruption():
    request = {'lines': ['1|a|63d73181', 'broken', '3|c|8e5d84c3']}
    before = copy.deepcopy(request)
    with pytest.raises(ValueError):
        run(request)
    assert request == before

def test_torn_tail():
    request = {'lines': ['1|a|63d73181', 'broken']}
    before = copy.deepcopy(request)
    assert run(request) == ['a']
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
