import copy
import pytest
from fabops.domain import run


def test_least_squares_not_endpoint_detrend():
    request = {'samples': [1, -2, 1, 0], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.4}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 0.0, 'band_energy': 0.666667, 'total_energy': 1.333333, 'ratio': 0.5, 'decision': 'alarm'}
    assert request == before

def test_sign_reversal_preserves_spectrum():
    request = {'samples': [-1, 2, -1, 0], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.4}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 0.0, 'band_energy': 0.666667, 'total_energy': 1.333333, 'ratio': 0.5, 'decision': 'alarm'}
    assert request == before

def test_energy_scales_quadratically():
    request = {'samples': [2, -2, -2, 2], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 0.0, 'band_energy': 2.666667, 'total_energy': 4.0, 'ratio': 0.666667, 'decision': 'alarm'}
    assert request == before

def test_nyquist_has_one_side_only():
    request = {'samples': [1, -2, 1, 0], 'sample_rate': 4, 'band': [2, 3], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.4}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 0.0, 'band_energy': 0.666667, 'total_energy': 1.333333, 'ratio': 0.5, 'decision': 'alarm'}
    assert request == before

def test_dc_not_doubled():
    request = {'samples': [1, -1, -1, 1], 'sample_rate': 4, 'band': [0, 1], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.1, 'ratio_threshold': 0.1}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 0.0, 'band_energy': 0.166667, 'total_energy': 1.0, 'ratio': 0.166667, 'decision': 'alarm'}
    assert request == before

def test_whole_spectrum_band():
    request = {'samples': [1, -1, -1, 1], 'sample_rate': 4, 'band': [0, 3], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 0.0, 'band_energy': 1.0, 'total_energy': 1.0, 'ratio': 1.0, 'decision': 'alarm'}
    assert request == before

def test_empty_band_has_zero_energy():
    request = {'samples': [1, -1, -1, 1], 'sample_rate': 4, 'band': [0.1, 0.9], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 0.0, 'band_energy': 0.0, 'total_energy': 1.0, 'ratio': 0.0, 'decision': 'normal'}
    assert request == before

def test_frequency_uses_rate_and_length():
    request = {'samples': [1, -1, -1, 1, 1, -1, -1, 1], 'sample_rate': 8, 'band': [2, 3], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 0.0, 'band_energy': 0.666667, 'total_energy': 1.0, 'ratio': 0.666667, 'decision': 'alarm'}
    assert request == before

def test_eight_sample_trend_and_offset():
    request = {'samples': [11, 12, 15, 20, 23, 24, 27, 32], 'sample_rate': 8, 'band': [2, 3], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 3.0, 'band_energy': 0.666667, 'total_energy': 1.0, 'ratio': 0.666667, 'decision': 'alarm'}
    assert request == before

def test_linear_interior_interpolation():
    request = {'samples': [1, None, -1, 1], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 0.75, 'slope': -0.1, 'band_energy': 0.6, 'total_energy': 1.11, 'ratio': 0.540541, 'decision': 'normal'}
    assert request == before

def test_two_holes_at_limit():
    request = {'samples': [1, None, None, 1], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 2, 'min_coverage': 0.5, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 0.5, 'slope': 0.0, 'band_energy': 0.0, 'total_energy': 0.0, 'ratio': 0.0, 'decision': 'normal'}
    assert request == before

def test_no_endpoint_extrapolation():
    request = {'samples': [None, 0, 0, 0], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 0.75, 'slope': None, 'band_energy': None, 'total_energy': None, 'ratio': None, 'decision': 'insufficient_data'}
    assert request == before

def test_hole_exceeds_limit():
    request = {'samples': [1, None, None, 1], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0.5, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 0.5, 'slope': None, 'band_energy': None, 'total_energy': None, 'ratio': None, 'decision': 'insufficient_data'}
    assert request == before

def test_all_samples_missing():
    request = {'samples': [None, None, None, None], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 0.0, 'slope': None, 'band_energy': None, 'total_energy': None, 'ratio': None, 'decision': 'insufficient_data'}
    assert request == before

def test_coverage_equality_is_accepted():
    request = {'samples': [1, None, -1, 1], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.54}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 0.75, 'slope': -0.1, 'band_energy': 0.6, 'total_energy': 1.11, 'ratio': 0.540541, 'decision': 'alarm'}
    assert request == before

def test_threshold_uses_unrounded_energy():
    request = {'samples': [1, -1, -1, 1], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.6666668, 'ratio_threshold': 0}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 0.0, 'band_energy': 0.666667, 'total_energy': 1.0, 'ratio': 0.666667, 'decision': 'normal'}
    assert request == before

def test_pure_linear_signal_has_zero_energy():
    request = {'samples': [1, 3, 5, 7], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 2.0, 'band_energy': 0.0, 'total_energy': 0.0, 'ratio': 0.0, 'decision': 'normal'}
    assert request == before

def test_zero_thresholds_are_inclusive():
    request = {'samples': [2, 2, 2, 2], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0, 'ratio_threshold': 0}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 0.0, 'band_energy': 0.0, 'total_energy': 0.0, 'ratio': 0.0, 'decision': 'alarm'}
    assert request == before

