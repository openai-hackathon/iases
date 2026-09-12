import copy
import pytest
from fabops.domain import run


def test_ordered_missing_cells():
    request = {'parts': ['q', 'p'], 'stations': ['other', 's'], 'measurements': [{'id': 'm', 'revision': 1, 'recorded': 1, 'event': 4, 'raw': '10', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}], 'calibrations': [{'id': 'c', 'revision': 1, 'recorded': 0, 'start': 0, 'end': 20, 'gain': '1', 'offset': '0', 'deleted': False}], 'quality': [], 'queries': [{'asof': 10, 'at': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == [[{'part': 'q', 'values': [None, None]}, {'part': 'p', 'values': [None, {'measurement': 'm', 'revision': 1, 'calibration_revision': 1, 'value': '10'}]}]]
    assert request == before

def test_future_correction_preserves_old_view():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'id': 'm', 'revision': 1, 'recorded': 1, 'event': 4, 'raw': '10', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}, {'id': 'm', 'revision': 2, 'recorded': 20, 'event': 4, 'raw': '30', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}], 'calibrations': [{'id': 'c', 'revision': 1, 'recorded': 0, 'start': 0, 'end': 20, 'gain': '1', 'offset': '0', 'deleted': False}], 'quality': [], 'queries': [{'asof': 10, 'at': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == [[{'part': 'p', 'values': [{'measurement': 'm', 'revision': 1, 'calibration_revision': 1, 'value': '10'}]}]]
    assert request == before

def test_measurement_time_calibration():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'id': 'm', 'revision': 1, 'recorded': 1, 'event': 4, 'raw': '10', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}], 'calibrations': [{'id': 'c', 'revision': 1, 'recorded': 0, 'start': 0, 'end': 5, 'gain': '1', 'offset': '0', 'deleted': False}], 'quality': [], 'queries': [{'asof': 10, 'at': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == [[{'part': 'p', 'values': [{'measurement': 'm', 'revision': 1, 'calibration_revision': 1, 'value': '10'}]}]]
    assert request == before

def test_quality_correction_suppresses_newest():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'id': 'old', 'revision': 1, 'recorded': 1, 'event': 1, 'raw': '10', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}, {'id': 'm', 'revision': 1, 'recorded': 1, 'event': 4, 'raw': '10', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}], 'calibrations': [{'id': 'c', 'revision': 1, 'recorded': 0, 'start': 0, 'end': 20, 'gain': '1', 'offset': '0', 'deleted': False}], 'quality': [{'id': 'm', 'revision': 1, 'recorded': 2, 'valid': False}], 'queries': [{'asof': 10, 'at': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == [[{'part': 'p', 'values': [None]}]]
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
