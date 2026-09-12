import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'sources': ['a'], 'commands': []}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [], 'snapshot': None, 'frontiers': {'a': [0, 1, -1]}}
    assert request == before

def test_one_source():
    request = {'sources': ['a'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'through': 1, 'watermark': 2, 'events': [{'sequence': 1, 'time': 2, 'value': 10}], 'crash': False}, {'op': 'snapshot'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'published'], 'snapshot': {'cut': 2, 'epochs': {'a': 0}, 'values': {'a': 10}}, 'frontiers': {'a': [0, 2, 2]}}
    assert request == before

def test_gap_survives_restart():
    request = {'sources': ['a'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'through': 2, 'watermark': 4, 'events': [{'sequence': 2, 'time': 4, 'value': 20}], 'crash': False}, {'op': 'snapshot'}, {'op': 'restart'}, {'op': 'page', 'source': 'a', 'epoch': 0, 'through': 1, 'watermark': 2, 'events': [{'sequence': 1, 'time': 2, 'value': 10}], 'crash': False}, {'op': 'snapshot'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'blocked', 'restarted', 'accepted', 'published'], 'snapshot': {'cut': 4, 'epochs': {'a': 0}, 'values': {'a': 20}}, 'frontiers': {'a': [0, 3, 4]}}
    assert request == before

def test_slow_source_cut():
    request = {'sources': ['a', 'b'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'through': 1, 'watermark': 5, 'events': [{'sequence': 1, 'time': 5, 'value': 50}], 'crash': False}, {'op': 'page', 'source': 'b', 'epoch': 0, 'through': 1, 'watermark': 2, 'events': [{'sequence': 1, 'time': 2, 'value': 20}], 'crash': False}, {'op': 'snapshot'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'accepted', 'published'], 'snapshot': {'cut': 2, 'epochs': {'a': 0, 'b': 0}, 'values': {'a': None, 'b': 20}}, 'frontiers': {'a': [0, 2, 5], 'b': [0, 2, 2]}}
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
