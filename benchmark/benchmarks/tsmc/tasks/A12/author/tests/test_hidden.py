import copy
import pytest
from fabops.domain import run


def test_later_query_sees_corrected_raw():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'id': 'm', 'revision': 1, 'recorded': 1, 'event': 4, 'raw': '10', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}, {'id': 'm', 'revision': 2, 'recorded': 20, 'event': 4, 'raw': '30', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}], 'calibrations': [{'id': 'c', 'revision': 1, 'recorded': 0, 'start': 0, 'end': 20, 'gain': '1', 'offset': '0', 'deleted': False}], 'quality': [], 'queries': [{'asof': 10, 'at': 10}, {'asof': 20, 'at': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == [[{'part': 'p', 'values': [{'measurement': 'm', 'revision': 1, 'calibration_revision': 1, 'value': '10'}]}], [{'part': 'p', 'values': [{'measurement': 'm', 'revision': 2, 'calibration_revision': 1, 'value': '30'}]}]]
    assert request == before

def test_queries_do_not_share_future_state():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'id': 'm', 'revision': 1, 'recorded': 1, 'event': 4, 'raw': '10', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}, {'id': 'm', 'revision': 2, 'recorded': 20, 'event': 4, 'raw': '30', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}], 'calibrations': [{'id': 'c', 'revision': 1, 'recorded': 0, 'start': 0, 'end': 20, 'gain': '1', 'offset': '0', 'deleted': False}], 'quality': [], 'queries': [{'asof': 20, 'at': 10}, {'asof': 10, 'at': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == [[{'part': 'p', 'values': [{'measurement': 'm', 'revision': 2, 'calibration_revision': 1, 'value': '30'}]}], [{'part': 'p', 'values': [{'measurement': 'm', 'revision': 1, 'calibration_revision': 1, 'value': '10'}]}]]
    assert request == before

def test_latest_event_not_latest_arrival():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'id': 'm', 'revision': 1, 'recorded': 1, 'event': 4, 'raw': '10', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}, {'id': 'late', 'revision': 1, 'recorded': 9, 'event': 2, 'raw': '99', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}], 'calibrations': [{'id': 'c', 'revision': 1, 'recorded': 0, 'start': 0, 'end': 20, 'gain': '1', 'offset': '0', 'deleted': False}], 'quality': [], 'queries': [{'asof': 10, 'at': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == [[{'part': 'p', 'values': [{'measurement': 'm', 'revision': 1, 'calibration_revision': 1, 'value': '10'}]}]]
    assert request == before

def test_tombstone_does_not_resurrect():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'id': 'm', 'revision': 1, 'recorded': 1, 'event': 4, 'raw': '10', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}, {'id': 'm', 'revision': 2, 'recorded': 5, 'event': 4, 'raw': '10', 'part': 'p', 'station': 's', 'valid': True, 'deleted': True, 'calibration': 'c'}], 'calibrations': [{'id': 'c', 'revision': 1, 'recorded': 0, 'start': 0, 'end': 20, 'gain': '1', 'offset': '0', 'deleted': False}], 'quality': [], 'queries': [{'asof': 10, 'at': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == [[{'part': 'p', 'values': [None]}]]
    assert request == before

def test_calibration_tombstone():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'id': 'm', 'revision': 1, 'recorded': 1, 'event': 4, 'raw': '10', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}], 'calibrations': [{'id': 'c', 'revision': 1, 'recorded': 0, 'start': 0, 'end': 20, 'gain': '1', 'offset': '0', 'deleted': False}, {'id': 'c', 'revision': 2, 'recorded': 5, 'start': 0, 'end': 20, 'gain': '1', 'offset': '0', 'deleted': True}], 'quality': [], 'queries': [{'asof': 10, 'at': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == [[{'part': 'p', 'values': [None]}]]
    assert request == before

def test_quality_revocation_then_clear():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'id': 'm', 'revision': 1, 'recorded': 1, 'event': 4, 'raw': '10', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}], 'calibrations': [{'id': 'c', 'revision': 1, 'recorded': 0, 'start': 0, 'end': 20, 'gain': '1', 'offset': '0', 'deleted': False}], 'quality': [{'id': 'm', 'revision': 1, 'recorded': 2, 'valid': False}, {'id': 'm', 'revision': 2, 'recorded': 7, 'valid': True}], 'queries': [{'asof': 5, 'at': 10}, {'asof': 7, 'at': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == [[{'part': 'p', 'values': [None]}], [{'part': 'p', 'values': [{'measurement': 'm', 'revision': 1, 'calibration_revision': 1, 'value': '10'}]}]]
    assert request == before

def test_future_quality_is_invisible():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'id': 'm', 'revision': 1, 'recorded': 1, 'event': 4, 'raw': '10', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}], 'calibrations': [{'id': 'c', 'revision': 1, 'recorded': 0, 'start': 0, 'end': 20, 'gain': '1', 'offset': '0', 'deleted': False}], 'quality': [{'id': 'm', 'revision': 1, 'recorded': 2, 'valid': True}, {'id': 'm', 'revision': 2, 'recorded': 30, 'valid': False}], 'queries': [{'asof': 10, 'at': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == [[{'part': 'p', 'values': [{'measurement': 'm', 'revision': 1, 'calibration_revision': 1, 'value': '10'}]}]]
    assert request == before

def test_future_calibration_preserves_known_revision():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'id': 'm', 'revision': 1, 'recorded': 1, 'event': 4, 'raw': '10', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}], 'calibrations': [{'id': 'c', 'revision': 1, 'recorded': 0, 'start': 0, 'end': 20, 'gain': '1', 'offset': '0', 'deleted': False}, {'id': 'c', 'revision': 2, 'recorded': 30, 'start': 0, 'end': 20, 'gain': '2', 'offset': '0', 'deleted': False}], 'quality': [], 'queries': [{'asof': 10, 'at': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == [[{'part': 'p', 'values': [{'measurement': 'm', 'revision': 1, 'calibration_revision': 1, 'value': '10'}]}]]
    assert request == before

def test_gain_and_offset_are_distinct():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'id': 'm', 'revision': 1, 'recorded': 1, 'event': 4, 'raw': '3/2', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}], 'calibrations': [{'id': 'c', 'revision': 1, 'recorded': 0, 'start': 0, 'end': 20, 'gain': '2', 'offset': '1/3', 'deleted': False}], 'quality': [], 'queries': [{'asof': 10, 'at': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == [[{'part': 'p', 'values': [{'measurement': 'm', 'revision': 1, 'calibration_revision': 1, 'value': '10/3'}]}]]
    assert request == before

def test_zero_and_negative():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'id': 'm', 'revision': 1, 'recorded': 1, 'event': 4, 'raw': '0', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}], 'calibrations': [{'id': 'c', 'revision': 1, 'recorded': 0, 'start': 0, 'end': 20, 'gain': '3', 'offset': '-2', 'deleted': False}], 'quality': [], 'queries': [{'asof': 10, 'at': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == [[{'part': 'p', 'values': [{'measurement': 'm', 'revision': 1, 'calibration_revision': 1, 'value': '-2'}]}]]
    assert request == before

def test_zero_preserved():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'id': 'm', 'revision': 1, 'recorded': 1, 'event': 4, 'raw': '0', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}], 'calibrations': [{'id': 'c', 'revision': 1, 'recorded': 0, 'start': 0, 'end': 20, 'gain': '1', 'offset': '0', 'deleted': False}], 'quality': [], 'queries': [{'asof': 10, 'at': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == [[{'part': 'p', 'values': [{'measurement': 'm', 'revision': 1, 'calibration_revision': 1, 'value': '0'}]}]]
    assert request == before

def test_newest_null_does_not_fallback():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'id': 'old', 'revision': 1, 'recorded': 1, 'event': 1, 'raw': '10', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}, {'id': 'm', 'revision': 1, 'recorded': 1, 'event': 4, 'raw': None, 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}], 'calibrations': [{'id': 'c', 'revision': 1, 'recorded': 0, 'start': 0, 'end': 20, 'gain': '1', 'offset': '0', 'deleted': False}], 'quality': [], 'queries': [{'asof': 10, 'at': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == [[{'part': 'p', 'values': [None]}]]
    assert request == before

def test_calibration_end_is_exclusive():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'id': 'm', 'revision': 1, 'recorded': 1, 'event': 4, 'raw': '10', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}], 'calibrations': [{'id': 'c', 'revision': 1, 'recorded': 0, 'start': 0, 'end': 4, 'gain': '1', 'offset': '0', 'deleted': False}], 'quality': [], 'queries': [{'asof': 10, 'at': 3}, {'asof': 10, 'at': 4}]}
    before = copy.deepcopy(request)
    assert run(request) == [[{'part': 'p', 'values': [None]}], [{'part': 'p', 'values': [None]}]]
    assert request == before

def test_event_cutoff_and_start_inclusive():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'id': 'm', 'revision': 1, 'recorded': 1, 'event': 4, 'raw': '10', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}], 'calibrations': [{'id': 'c', 'revision': 1, 'recorded': 0, 'start': 4, 'end': 20, 'gain': '1', 'offset': '0', 'deleted': False}], 'quality': [], 'queries': [{'asof': 1, 'at': 4}]}
    before = copy.deepcopy(request)
    assert run(request) == [[{'part': 'p', 'values': [{'measurement': 'm', 'revision': 1, 'calibration_revision': 1, 'value': '10'}]}]]
    assert request == before

def test_event_tie_uses_id():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'id': 'a', 'revision': 1, 'recorded': 1, 'event': 4, 'raw': '1', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}, {'id': 'z', 'revision': 1, 'recorded': 1, 'event': 4, 'raw': '2', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}], 'calibrations': [{'id': 'c', 'revision': 1, 'recorded': 0, 'start': 0, 'end': 20, 'gain': '1', 'offset': '0', 'deleted': False}], 'quality': [], 'queries': [{'asof': 10, 'at': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == [[{'part': 'p', 'values': [{'measurement': 'z', 'revision': 1, 'calibration_revision': 1, 'value': '2'}]}]]
    assert request == before

def test_unknown_calibration_does_not_fallback():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'id': 'old', 'revision': 1, 'recorded': 1, 'event': 1, 'raw': '10', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}, {'id': 'm', 'revision': 1, 'recorded': 1, 'event': 4, 'raw': '10', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'absent'}], 'calibrations': [{'id': 'c', 'revision': 1, 'recorded': 0, 'start': 0, 'end': 20, 'gain': '1', 'offset': '0', 'deleted': False}], 'quality': [], 'queries': [{'asof': 10, 'at': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == [[{'part': 'p', 'values': [None]}]]
    assert request == before

def test_quality_overrides_raw_flag():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'id': 'm', 'revision': 1, 'recorded': 1, 'event': 4, 'raw': '10', 'part': 'p', 'station': 's', 'valid': False, 'deleted': False, 'calibration': 'c'}], 'calibrations': [{'id': 'c', 'revision': 1, 'recorded': 0, 'start': 0, 'end': 20, 'gain': '1', 'offset': '0', 'deleted': False}], 'quality': [{'id': 'm', 'revision': 1, 'recorded': 2, 'valid': True}], 'queries': [{'asof': 10, 'at': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == [[{'part': 'p', 'values': [{'measurement': 'm', 'revision': 1, 'calibration_revision': 1, 'value': '10'}]}]]
    assert request == before

def test_greatest_revision_not_recorded_time():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'id': 'm', 'revision': 3, 'recorded': 2, 'event': 4, 'raw': '3', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}, {'id': 'm', 'revision': 2, 'recorded': 8, 'event': 4, 'raw': '2', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}], 'calibrations': [{'id': 'c', 'revision': 1, 'recorded': 0, 'start': 0, 'end': 20, 'gain': '1', 'offset': '0', 'deleted': False}], 'quality': [], 'queries': [{'asof': 10, 'at': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == [[{'part': 'p', 'values': [{'measurement': 'm', 'revision': 3, 'calibration_revision': 1, 'value': '3'}]}]]
    assert request == before

def test_calibration_interval_corrected():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'id': 'm', 'revision': 1, 'recorded': 1, 'event': 4, 'raw': '10', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}], 'calibrations': [{'id': 'c', 'revision': 1, 'recorded': 0, 'start': 0, 'end': 20, 'gain': '1', 'offset': '0', 'deleted': False}, {'id': 'c', 'revision': 2, 'recorded': 5, 'start': 6, 'end': 20, 'gain': '1', 'offset': '0', 'deleted': False}], 'quality': [], 'queries': [{'asof': 4, 'at': 10}, {'asof': 5, 'at': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == [[{'part': 'p', 'values': [{'measurement': 'm', 'revision': 1, 'calibration_revision': 1, 'value': '10'}]}], [{'part': 'p', 'values': [None]}]]
    assert request == before

def test_all_cells_unavailable():
    request = {'parts': ['q', 'p'], 'stations': ['s'], 'measurements': [], 'calibrations': [{'id': 'c', 'revision': 1, 'recorded': 0, 'start': 0, 'end': 20, 'gain': '1', 'offset': '0', 'deleted': False}], 'quality': [], 'queries': [{'asof': 10, 'at': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == [[{'part': 'q', 'values': [None]}, {'part': 'p', 'values': [None]}]]
    assert request == before

def test_no_stations():
    request = {'parts': ['p'], 'stations': [], 'measurements': [{'id': 'm', 'revision': 1, 'recorded': 1, 'event': 4, 'raw': '10', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}], 'calibrations': [{'id': 'c', 'revision': 1, 'recorded': 0, 'start': 0, 'end': 20, 'gain': '1', 'offset': '0', 'deleted': False}], 'quality': [], 'queries': [{'asof': 10, 'at': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == [[{'part': 'p', 'values': []}]]
    assert request == before

def test_hidden_quality_correction_blocks_older_fallback():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'id': 'old', 'revision': 1, 'recorded': 1, 'event': 1, 'raw': '10', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}, {'id': 'm', 'revision': 1, 'recorded': 1, 'event': 4, 'raw': '10', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}], 'calibrations': [{'id': 'c', 'revision': 1, 'recorded': 0, 'start': 0, 'end': 20, 'gain': '1', 'offset': '0', 'deleted': False}], 'quality': [{'id': 'm', 'revision': 1, 'recorded': 5, 'valid': False}], 'queries': [{'asof': 4, 'at': 10}, {'asof': 5, 'at': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == [[{'part': 'p', 'values': [{'measurement': 'm', 'revision': 1, 'calibration_revision': 1, 'value': '10'}]}], [{'part': 'p', 'values': [None]}]]
    assert request == before

def test_newer_raw_invalid_blocks_older_fallback():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'id': 'old', 'revision': 1, 'recorded': 1, 'event': 1, 'raw': '10', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}, {'id': 'm', 'revision': 1, 'recorded': 1, 'event': 4, 'raw': '10', 'part': 'p', 'station': 's', 'valid': False, 'deleted': False, 'calibration': 'c'}], 'calibrations': [{'id': 'c', 'revision': 1, 'recorded': 0, 'start': 0, 'end': 20, 'gain': '1', 'offset': '0', 'deleted': False}], 'quality': [], 'queries': [{'asof': 10, 'at': 10}]}
    before = copy.deepcopy(request)
    assert run(request) == [[{'part': 'p', 'values': [None]}]]
    assert request == before

def test_no_queries():
    request = {'parts': ['p'], 'stations': ['s'], 'measurements': [{'id': 'm', 'revision': 1, 'recorded': 1, 'event': 4, 'raw': '10', 'part': 'p', 'station': 's', 'valid': True, 'deleted': False, 'calibration': 'c'}], 'calibrations': [{'id': 'c', 'revision': 1, 'recorded': 0, 'start': 0, 'end': 20, 'gain': '1', 'offset': '0', 'deleted': False}], 'quality': [], 'queries': []}
    before = copy.deepcopy(request)
    assert run(request) == []
    assert request == before

