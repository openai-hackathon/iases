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

def test_missing_dependency_retreats():
    request = {'sources': ['a', 'b'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'events': [{'sequence': 1, 'time': 1, 'value': 10, 'depends': [['b', 0, 1]]}], 'through': 1, 'watermark': 10}, {'op': 'page', 'source': 'b', 'epoch': 0, 'events': [], 'through': 0, 'watermark': 10}, {'op': 'snapshot'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'accepted', 'published'], 'snapshot': {'cut': 10, 'epochs': {'a': 0, 'b': 0}, 'values': {'a': None, 'b': None}}, 'frontiers': {'a': [0, 2, 10], 'b': [0, 1, 10]}}
    assert request == before

def test_dependency_recovers_after_restart():
    request = {'sources': ['a', 'b'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'events': [{'sequence': 1, 'time': 1, 'value': 10, 'depends': [['b', 0, 1]]}], 'through': 1, 'watermark': 10}, {'op': 'page', 'source': 'b', 'epoch': 0, 'events': [], 'through': 0, 'watermark': 10}, {'op': 'snapshot'}, {'op': 'restart'}, {'op': 'page', 'source': 'b', 'epoch': 0, 'events': [{'sequence': 1, 'time': 11, 'value': 20, 'depends': []}], 'through': 1, 'watermark': 20}, {'op': 'page', 'source': 'a', 'epoch': 0, 'events': [], 'through': 1, 'watermark': 20}, {'op': 'snapshot'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'accepted', 'published', 'restarted', 'accepted', 'accepted', 'published'], 'snapshot': {'cut': 20, 'epochs': {'a': 0, 'b': 0}, 'values': {'a': 10, 'b': 20}}, 'frontiers': {'a': [0, 2, 20], 'b': [0, 2, 20]}}
    assert request == before

def test_fixed_point_cascade():
    request = {'sources': ['a', 'b', 'c'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'events': [{'sequence': 1, 'time': 1, 'value': 1, 'depends': [['b', 0, 1]]}], 'through': 1, 'watermark': 10}, {'op': 'page', 'source': 'b', 'epoch': 0, 'events': [{'sequence': 1, 'time': 1, 'value': 2, 'depends': [['c', 0, 1]]}], 'through': 1, 'watermark': 10}, {'op': 'page', 'source': 'c', 'epoch': 0, 'events': [], 'through': 0, 'watermark': 10}, {'op': 'snapshot'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'accepted', 'accepted', 'published'], 'snapshot': {'cut': 10, 'epochs': {'a': 0, 'b': 0, 'c': 0}, 'values': {'a': None, 'b': None, 'c': None}}, 'frontiers': {'a': [0, 2, 10], 'b': [0, 2, 10], 'c': [0, 1, 10]}}
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
