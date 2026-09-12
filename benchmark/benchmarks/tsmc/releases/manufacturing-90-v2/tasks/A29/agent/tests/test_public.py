import copy
import pytest
from fabops.domain import run


def test_constant_phases():
    request = {'cycles': [{'id': 'c', 'start': 0, 'end': 4}], 'pressure': [{'cycle': 'c', 't': 0, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 4, 'value': 60, 'valid': True}], 'flow': [{'cycle': 'c', 't': 0, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 4, 'value': 60, 'valid': True}], 'max_gap': {'pressure': 4, 'flow': 4}, 'min_coverage': 1, 'calibration': {'pressure': {'gain': 1, 'offset': 0}, 'flow': {'gain': 1, 'offset': 0}}}
    before = copy.deepcopy(request)
    assert run(request) == [{'cycle': 'c', 'coverage': 1.0, 'accepted': True, 'volume': 4.0, 'work': 24.0}]
    assert request == before

def test_affine_product():
    request = {'cycles': [{'id': 'c', 'start': 0, 'end': 4}], 'pressure': [{'cycle': 'c', 't': 0, 'value': 0, 'valid': True}, {'cycle': 'c', 't': 4, 'value': 120, 'valid': True}], 'flow': [{'cycle': 'c', 't': 0, 'value': 0, 'valid': True}, {'cycle': 'c', 't': 4, 'value': 120, 'valid': True}], 'max_gap': {'pressure': 4, 'flow': 4}, 'min_coverage': 1, 'calibration': {'pressure': {'gain': 1, 'offset': 0}, 'flow': {'gain': 1, 'offset': 0}}}
    before = copy.deepcopy(request)
    assert run(request) == [{'cycle': 'c', 'coverage': 1.0, 'accepted': True, 'volume': 4.0, 'work': 32.0}]
    assert request == before

def test_bad_knot_breaks_both_neighbors():
    request = {'cycles': [{'id': 'c', 'start': 0, 'end': 4}], 'pressure': [{'cycle': 'c', 't': 0, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 1, 'value': 60, 'valid': False}, {'cycle': 'c', 't': 2, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 4, 'value': 60, 'valid': True}], 'flow': [{'cycle': 'c', 't': 0, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 4, 'value': 60, 'valid': True}], 'max_gap': {'pressure': 4, 'flow': 4}, 'min_coverage': 0.5, 'calibration': {'pressure': {'gain': 1, 'offset': 0}, 'flow': {'gain': 1, 'offset': 0}}}
    before = copy.deepcopy(request)
    assert run(request) == [{'cycle': 'c', 'coverage': 0.5, 'accepted': True, 'volume': 2.0, 'work': 12.0}]
    assert request == before

def test_individually_covered_but_disjoint():
    request = {'cycles': [{'id': 'c', 'start': 0, 'end': 4}], 'pressure': [{'cycle': 'c', 't': 0, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 2, 'value': 60, 'valid': True}], 'flow': [{'cycle': 'c', 't': 2, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 4, 'value': 60, 'valid': True}], 'max_gap': {'pressure': 4, 'flow': 4}, 'min_coverage': 0.5, 'calibration': {'pressure': {'gain': 1, 'offset': 0}, 'flow': {'gain': 1, 'offset': 0}}}
    before = copy.deepcopy(request)
    assert run(request) == [{'cycle': 'c', 'coverage': 0.0, 'accepted': False, 'volume': None, 'work': None}]
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
