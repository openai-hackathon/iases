import copy
import pytest
from fabops.domain import run


def test_gap_rejects_sparse_span():
    request = {'cycles': [{'id': 'c', 'start': 0, 'end': 4}], 'pressure': [{'cycle': 'c', 't': 0, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 1, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 4, 'value': 60, 'valid': True}], 'flow': [{'cycle': 'c', 't': 0, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 4, 'value': 60, 'valid': True}], 'max_gap': {'pressure': 2, 'flow': 2}, 'min_coverage': 0.1, 'calibration': {'pressure': {'gain': 1, 'offset': 0}, 'flow': {'gain': 1, 'offset': 0}}}
    before = copy.deepcopy(request)
    assert run(request) == [{'cycle': 'c', 'coverage': 0.0, 'accepted': False, 'volume': None, 'work': None}]
    assert request == before

def test_gap_equality_is_supported():
    request = {'cycles': [{'id': 'c', 'start': 0, 'end': 4}], 'pressure': [{'cycle': 'c', 't': 0, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 2, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 4, 'value': 60, 'valid': True}], 'flow': [{'cycle': 'c', 't': 0, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 2, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 4, 'value': 60, 'valid': True}], 'max_gap': {'pressure': 2, 'flow': 2}, 'min_coverage': 1, 'calibration': {'pressure': {'gain': 1, 'offset': 0}, 'flow': {'gain': 1, 'offset': 0}}}
    before = copy.deepcopy(request)
    assert run(request) == [{'cycle': 'c', 'coverage': 1.0, 'accepted': True, 'volume': 4.0, 'work': 24.0}]
    assert request == before

def test_knots_from_either_channel():
    request = {'cycles': [{'id': 'c', 'start': 0, 'end': 4}], 'pressure': [{'cycle': 'c', 't': 0, 'value': 0, 'valid': True}, {'cycle': 'c', 't': 4, 'value': 120, 'valid': True}], 'flow': [{'cycle': 'c', 't': 0, 'value': 0, 'valid': True}, {'cycle': 'c', 't': 2, 'value': 120, 'valid': True}, {'cycle': 'c', 't': 4, 'value': 0, 'valid': True}], 'max_gap': {'pressure': 4, 'flow': 4}, 'min_coverage': 1, 'calibration': {'pressure': {'gain': 1, 'offset': 0}, 'flow': {'gain': 1, 'offset': 0}}}
    before = copy.deepcopy(request)
    assert run(request) == [{'cycle': 'c', 'coverage': 1.0, 'accepted': True, 'volume': 4.0, 'work': 24.0}]
    assert request == before

def test_crossed_affine_slopes():
    request = {'cycles': [{'id': 'c', 'start': 0, 'end': 4}], 'pressure': [{'cycle': 'c', 't': 0, 'value': 120, 'valid': True}, {'cycle': 'c', 't': 4, 'value': 0, 'valid': True}], 'flow': [{'cycle': 'c', 't': 0, 'value': 0, 'valid': True}, {'cycle': 'c', 't': 4, 'value': 120, 'valid': True}], 'max_gap': {'pressure': 4, 'flow': 4}, 'min_coverage': 1, 'calibration': {'pressure': {'gain': 1, 'offset': 0}, 'flow': {'gain': 1, 'offset': 0}}}
    before = copy.deepcopy(request)
    assert run(request) == [{'cycle': 'c', 'coverage': 1.0, 'accepted': True, 'volume': 4.0, 'work': 16.0}]
    assert request == before

def test_calibrate_before_product():
    request = {'cycles': [{'id': 'c', 'start': 0, 'end': 4}], 'pressure': [{'cycle': 'c', 't': 0, 'value': 0, 'valid': True}, {'cycle': 'c', 't': 4, 'value': 60, 'valid': True}], 'flow': [{'cycle': 'c', 't': 0, 'value': 0, 'valid': True}, {'cycle': 'c', 't': 4, 'value': 60, 'valid': True}], 'max_gap': {'pressure': 4, 'flow': 4}, 'min_coverage': 1, 'calibration': {'pressure': {'gain': 2, 'offset': 60}, 'flow': {'gain': 1, 'offset': 30}}}
    before = copy.deepcopy(request)
    assert run(request) == [{'cycle': 'c', 'coverage': 1.0, 'accepted': True, 'volume': 4.0, 'work': 52.0}]
    assert request == before

def test_coverage_gate_uses_full_cycle():
    request = {'cycles': [{'id': 'c', 'start': 0, 'end': 4}], 'pressure': [{'cycle': 'c', 't': 1, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 3, 'value': 60, 'valid': True}], 'flow': [{'cycle': 'c', 't': 1, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 3, 'value': 60, 'valid': True}], 'max_gap': {'pressure': 4, 'flow': 4}, 'min_coverage': 0.6, 'calibration': {'pressure': {'gain': 1, 'offset': 0}, 'flow': {'gain': 1, 'offset': 0}}}
    before = copy.deepcopy(request)
    assert run(request) == [{'cycle': 'c', 'coverage': 0.5, 'accepted': False, 'volume': None, 'work': None}]
    assert request == before

def test_joint_not_marginal_coverage():
    request = {'cycles': [{'id': 'c', 'start': 0, 'end': 4}], 'pressure': [{'cycle': 'c', 't': 0, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 3, 'value': 60, 'valid': True}], 'flow': [{'cycle': 'c', 't': 1, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 4, 'value': 60, 'valid': True}], 'max_gap': {'pressure': 4, 'flow': 4}, 'min_coverage': 0.6, 'calibration': {'pressure': {'gain': 1, 'offset': 0}, 'flow': {'gain': 1, 'offset': 0}}}
    before = copy.deepcopy(request)
    assert run(request) == [{'cycle': 'c', 'coverage': 0.5, 'accepted': False, 'volume': None, 'work': None}]
    assert request == before

def test_single_observation_cannot_extrapolate():
    request = {'cycles': [{'id': 'c', 'start': 0, 'end': 4}], 'pressure': [{'cycle': 'c', 't': 2, 'value': 60, 'valid': True}], 'flow': [{'cycle': 'c', 't': 0, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 4, 'value': 60, 'valid': True}], 'max_gap': {'pressure': 4, 'flow': 4}, 'min_coverage': 0, 'calibration': {'pressure': {'gain': 1, 'offset': 0}, 'flow': {'gain': 1, 'offset': 0}}}
    before = copy.deepcopy(request)
    assert run(request) == [{'cycle': 'c', 'coverage': 0.0, 'accepted': False, 'volume': None, 'work': None}]
    assert request == before

def test_empty_channel():
    request = {'cycles': [{'id': 'c', 'start': 0, 'end': 4}], 'pressure': [], 'flow': [{'cycle': 'c', 't': 0, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 4, 'value': 60, 'valid': True}], 'max_gap': {'pressure': 4, 'flow': 4}, 'min_coverage': 0, 'calibration': {'pressure': {'gain': 1, 'offset': 0}, 'flow': {'gain': 1, 'offset': 0}}}
    before = copy.deepcopy(request)
    assert run(request) == [{'cycle': 'c', 'coverage': 0.0, 'accepted': False, 'volume': None, 'work': None}]
    assert request == before

def test_unsorted_inputs():
    request = {'cycles': [{'id': 'c', 'start': 0, 'end': 4}], 'pressure': [{'cycle': 'c', 't': 4, 'value': 120, 'valid': True}, {'cycle': 'c', 't': 0, 'value': 0, 'valid': True}], 'flow': [{'cycle': 'c', 't': 4, 'value': 120, 'valid': True}, {'cycle': 'c', 't': 0, 'value': 0, 'valid': True}], 'max_gap': {'pressure': 4, 'flow': 4}, 'min_coverage': 1, 'calibration': {'pressure': {'gain': 1, 'offset': 0}, 'flow': {'gain': 1, 'offset': 0}}}
    before = copy.deepcopy(request)
    assert run(request) == [{'cycle': 'c', 'coverage': 1.0, 'accepted': True, 'volume': 4.0, 'work': 32.0}]
    assert request == before

def test_bad_rows_are_not_removed_before_adjacency():
    request = {'cycles': [{'id': 'c', 'start': 0, 'end': 4}], 'pressure': [{'cycle': 'c', 't': 0, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 2, 'value': 60, 'valid': False}, {'cycle': 'c', 't': 4, 'value': 60, 'valid': True}], 'flow': [{'cycle': 'c', 't': 0, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 4, 'value': 60, 'valid': True}], 'max_gap': {'pressure': 4, 'flow': 4}, 'min_coverage': 0, 'calibration': {'pressure': {'gain': 1, 'offset': 0}, 'flow': {'gain': 1, 'offset': 0}}}
    before = copy.deepcopy(request)
    assert run(request) == [{'cycle': 'c', 'coverage': 0.0, 'accepted': False, 'volume': None, 'work': None}]
    assert request == before

def test_outside_rows_do_not_extend_support():
    request = {'cycles': [{'id': 'c', 'start': 0, 'end': 4}], 'pressure': [{'cycle': 'c', 't': -1, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 1, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 3, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 5, 'value': 60, 'valid': True}], 'flow': [{'cycle': 'c', 't': 0, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 4, 'value': 60, 'valid': True}], 'max_gap': {'pressure': 4, 'flow': 4}, 'min_coverage': 0.5, 'calibration': {'pressure': {'gain': 1, 'offset': 0}, 'flow': {'gain': 1, 'offset': 0}}}
    before = copy.deepcopy(request)
    assert run(request) == [{'cycle': 'c', 'coverage': 0.5, 'accepted': True, 'volume': 2.0, 'work': 12.0}]
    assert request == before

def test_cycle_boundary_identity():
    request = {'cycles': [{'id': 'b', 'start': 4, 'end': 8}, {'id': 'c', 'start': 0, 'end': 4}], 'pressure': [{'cycle': 'c', 't': 0, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 4, 'value': 60, 'valid': True}, {'cycle': 'b', 't': 4, 'value': 120, 'valid': True}, {'cycle': 'b', 't': 8, 'value': 120, 'valid': True}], 'flow': [{'cycle': 'c', 't': 0, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 4, 'value': 60, 'valid': True}, {'cycle': 'b', 't': 4, 'value': 30, 'valid': True}, {'cycle': 'b', 't': 8, 'value': 30, 'valid': True}], 'max_gap': {'pressure': 4, 'flow': 4}, 'min_coverage': 1, 'calibration': {'pressure': {'gain': 1, 'offset': 0}, 'flow': {'gain': 1, 'offset': 0}}}
    before = copy.deepcopy(request)
    assert run(request) == [{'cycle': 'c', 'coverage': 1.0, 'accepted': True, 'volume': 4.0, 'work': 24.0}, {'cycle': 'b', 'coverage': 1.0, 'accepted': True, 'volume': 2.0, 'work': 24.0}]
    assert request == before

def test_gate_before_rounding():
    request = {'cycles': [{'id': 'c', 'start': 0, 'end': 3}], 'pressure': [{'cycle': 'c', 't': 0, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 1, 'value': 60, 'valid': True}], 'flow': [{'cycle': 'c', 't': 0, 'value': 60, 'valid': True}, {'cycle': 'c', 't': 1, 'value': 60, 'valid': True}], 'max_gap': {'pressure': 4, 'flow': 4}, 'min_coverage': 0.3333334, 'calibration': {'pressure': {'gain': 1, 'offset': 0}, 'flow': {'gain': 1, 'offset': 0}}}
    before = copy.deepcopy(request)
    assert run(request) == [{'cycle': 'c', 'coverage': 0.333333, 'accepted': False, 'volume': None, 'work': None}]
    assert request == before

