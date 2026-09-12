import copy
import pytest
from fabops.domain import run


def test_least_squares_not_endpoint_detrend():
    request = {'samples': [1, -2, 1, 0], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.4}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 0.0, 'band_energy': 0.666667, 'total_energy': 1.333333, 'ratio': 0.5, 'decision': 'alarm', 'segments': [0], 'reference_energy': 0.666667, 'coherence': 1.0, 'phase': 0.0}
    assert request == before

def test_sign_reversal_preserves_spectrum():
    request = {'samples': [-1, 2, -1, 0], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.4}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 0.0, 'band_energy': 0.666667, 'total_energy': 1.333333, 'ratio': 0.5, 'decision': 'alarm', 'segments': [0], 'reference_energy': 0.666667, 'coherence': 1.0, 'phase': 0.0}
    assert request == before

def test_energy_scales_quadratically():
    request = {'samples': [2, -2, -2, 2], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 0.0, 'band_energy': 2.666667, 'total_energy': 4.0, 'ratio': 0.666667, 'decision': 'alarm', 'segments': [0], 'reference_energy': 2.666667, 'coherence': 1.0, 'phase': 0.0}
    assert request == before

def test_nyquist_has_one_side_only():
    request = {'samples': [1, -2, 1, 0], 'sample_rate': 4, 'band': [2, 3], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.4}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 0.0, 'band_energy': 0.666667, 'total_energy': 1.333333, 'ratio': 0.5, 'decision': 'alarm', 'segments': [0], 'reference_energy': 0.666667, 'coherence': 1.0, 'phase': 0.0}
    assert request == before

def test_dc_not_doubled():
    request = {'samples': [1, -1, -1, 1], 'sample_rate': 4, 'band': [0, 1], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.1, 'ratio_threshold': 0.1}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 0.0, 'band_energy': 0.166667, 'total_energy': 1.0, 'ratio': 0.166667, 'decision': 'alarm', 'segments': [0], 'reference_energy': 0.166667, 'coherence': 1.0, 'phase': 0.0}
    assert request == before

def test_whole_spectrum_band():
    request = {'samples': [1, -1, -1, 1], 'sample_rate': 4, 'band': [0, 3], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 0.0, 'band_energy': 1.0, 'total_energy': 1.0, 'ratio': 1.0, 'decision': 'alarm', 'segments': [0], 'reference_energy': 1.0, 'coherence': 1.0, 'phase': 0.0}
    assert request == before

def test_empty_band_has_zero_energy():
    request = {'samples': [1, -1, -1, 1], 'sample_rate': 4, 'band': [0.1, 0.9], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 0.0, 'band_energy': 0.0, 'total_energy': 1.0, 'ratio': 0.0, 'decision': 'normal', 'segments': [0], 'reference_energy': 0.0, 'coherence': 0.0, 'phase': 0.0}
    assert request == before

def test_frequency_uses_rate_and_length():
    request = {'samples': [1, -1, -1, 1, 1, -1, -1, 1], 'sample_rate': 8, 'band': [2, 3], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 0.0, 'band_energy': 0.666667, 'total_energy': 1.0, 'ratio': 0.666667, 'decision': 'alarm', 'segments': [0], 'reference_energy': 0.666667, 'coherence': 1.0, 'phase': 0.0}
    assert request == before

def test_eight_sample_trend_and_offset():
    request = {'samples': [11, 12, 15, 20, 23, 24, 27, 32], 'sample_rate': 8, 'band': [2, 3], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 3.0, 'band_energy': 0.666667, 'total_energy': 1.0, 'ratio': 0.666667, 'decision': 'alarm', 'segments': [0], 'reference_energy': 0.666667, 'coherence': 1.0, 'phase': 0.0}
    assert request == before

def test_linear_interior_interpolation():
    request = {'samples': [1, None, -1, 1], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 0.75, 'slope': -0.1, 'band_energy': 0.6, 'total_energy': 1.11, 'ratio': 0.540541, 'decision': 'normal', 'segments': [0], 'reference_energy': 0.6, 'coherence': 1.0, 'phase': 0.0}
    assert request == before

def test_two_holes_at_limit():
    request = {'samples': [1, None, None, 1], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 2, 'min_coverage': 0.5, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 0.5, 'slope': 0.0, 'band_energy': 0.0, 'total_energy': 0.0, 'ratio': 0.0, 'decision': 'normal', 'segments': [0], 'reference_energy': 0.0, 'coherence': 0.0, 'phase': 0.0}
    assert request == before

def test_no_endpoint_extrapolation():
    request = {'samples': [None, 0, 0, 0], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 0.75, 'slope': None, 'band_energy': None, 'total_energy': None, 'ratio': None, 'decision': 'insufficient_data', 'segments': [], 'reference_energy': None, 'coherence': None, 'phase': None}
    assert request == before

def test_hole_exceeds_limit():
    request = {'samples': [1, None, None, 1], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0.5, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 0.5, 'slope': None, 'band_energy': None, 'total_energy': None, 'ratio': None, 'decision': 'insufficient_data', 'segments': [], 'reference_energy': None, 'coherence': None, 'phase': None}
    assert request == before

def test_all_samples_missing():
    request = {'samples': [None, None, None, None], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 0.0, 'slope': None, 'band_energy': None, 'total_energy': None, 'ratio': None, 'decision': 'insufficient_data', 'segments': [], 'reference_energy': None, 'coherence': None, 'phase': None}
    assert request == before

def test_coverage_equality_is_accepted():
    request = {'samples': [1, None, -1, 1], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.54}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 0.75, 'slope': -0.1, 'band_energy': 0.6, 'total_energy': 1.11, 'ratio': 0.540541, 'decision': 'alarm', 'segments': [0], 'reference_energy': 0.6, 'coherence': 1.0, 'phase': 0.0}
    assert request == before

def test_threshold_uses_unrounded_energy():
    request = {'samples': [1, -1, -1, 1], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.6666668, 'ratio_threshold': 0}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 0.0, 'band_energy': 0.666667, 'total_energy': 1.0, 'ratio': 0.666667, 'decision': 'normal', 'segments': [0], 'reference_energy': 0.666667, 'coherence': 1.0, 'phase': 0.0}
    assert request == before

def test_pure_linear_signal_has_zero_energy():
    request = {'samples': [1, 3, 5, 7], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 2.0, 'band_energy': 0.0, 'total_energy': 0.0, 'ratio': 0.0, 'decision': 'normal', 'segments': [0], 'reference_energy': 0.0, 'coherence': 0.0, 'phase': 0.0}
    assert request == before

def test_zero_thresholds_are_inclusive():
    request = {'samples': [2, 2, 2, 2], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0, 'ratio_threshold': 0}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 0.0, 'band_energy': 0.0, 'total_energy': 0.0, 'ratio': 0.0, 'decision': 'alarm', 'segments': [0], 'reference_energy': 0.0, 'coherence': 0.0, 'phase': 0.0}
    assert request == before

def test_signed_phase_1():
    request = {'band': [0, 3], 'coherence_threshold': 0.5, 'energy_threshold': 0.01, 'max_gap': 1, 'min_coverage': 0.5, 'phase_limit': 3.141592653589793, 'ratio_threshold': 0, 'reference': [0, -1, 0, 1, 0, -1, 0, 1], 'sample_rate': 4, 'samples': [0, 1, 0, -1, 0, 1, 0, -1], 'segment_length': 4, 'step': 4}
    before = copy.deepcopy(request)
    assert run(request) == {'band_energy': 0.16, 'coherence': 1, 'coverage': 1.0, 'decision': 'alarm', 'phase': 3.141593, 'ratio': 1.0, 'reference_energy': 0.16, 'segments': [0, 4], 'slope': -0.4, 'total_energy': 0.16}
    assert request == before

def test_signed_phase_2():
    request = {'band': [0, 3], 'coherence_threshold': 0.5, 'energy_threshold': 0.01, 'max_gap': 1, 'min_coverage': 0.5, 'phase_limit': 3.141592653589793, 'ratio_threshold': 0, 'reference': [-1, 0, 1, 0, -1, 0, 1, 0], 'sample_rate': 4, 'samples': [0, 1, 0, -1, 0, 1, 0, -1], 'segment_length': 4, 'step': 4}
    before = copy.deepcopy(request)
    assert run(request) == {'band_energy': 0.16, 'coherence': 0.605856, 'coverage': 1.0, 'decision': 'alarm', 'phase': -0.655696, 'ratio': 1.0, 'reference_energy': 0.493333, 'segments': [0, 4], 'slope': -0.4, 'total_energy': 0.16}
    assert request == before

def test_overlap_with_local_reference_gap():
    request = {'band': [0, 3], 'coherence_threshold': 0.5, 'energy_threshold': 0.01, 'max_gap': 1, 'min_coverage': 0.5, 'phase_limit': 3.141592653589793, 'ratio_threshold': 0, 'reference': [0, None, 0, -1, 0, -1, 0, 1], 'sample_rate': 4, 'samples': [0, 1, 0, -1, 0, 1, 0, -1], 'segment_length': 4, 'step': 2}
    before = copy.deepcopy(request)
    assert run(request) == {'band_energy': 0.16, 'coherence': 0.042216, 'coverage': 0.875, 'decision': 'normal', 'phase': 2.485897, 'ratio': 1.0, 'reference_energy': 0.196667, 'segments': [0, 2, 4], 'slope': -0.133333, 'total_energy': 0.16}
    assert request == before

def test_reference_endpoint_rejects_pair():
    request = {'band': [0, 3], 'coherence_threshold': 0.5, 'energy_threshold': 0.01, 'max_gap': 1, 'min_coverage': 0.5, 'phase_limit': 3.141592653589793, 'ratio_threshold': 0, 'reference': [0, 1, 0, -1, None, -1, 0, 1], 'sample_rate': 4, 'samples': [0, 1, 0, -1, 0, 1, 0, -1], 'segment_length': 4, 'step': 4}
    before = copy.deepcopy(request)
    assert run(request) == {'band_energy': 0.16, 'coherence': 1, 'coverage': 0.875, 'decision': 'alarm', 'phase': -0.0, 'ratio': 1.0, 'reference_energy': 0.16, 'segments': [0], 'slope': -0.4, 'total_energy': 0.16}
    assert request == before

def test_independent_interior_gap_repair():
    request = {'band': [0, 3], 'coherence_threshold': 0.5, 'energy_threshold': 0.01, 'max_gap': 1, 'min_coverage': 0.5, 'phase_limit': 3.141592653589793, 'ratio_threshold': 0, 'reference': [0, 1, 0, -1, 0, -1, None, 1], 'sample_rate': 4, 'samples': [0, None, 0, -1, 0, 1, 0, -1], 'segment_length': 4, 'step': 4}
    before = copy.deepcopy(request)
    assert run(request) == {'band_energy': 0.141667, 'coherence': 0.108333, 'coverage': 0.75, 'decision': 'normal', 'phase': 2.403778, 'ratio': 1.0, 'reference_energy': 0.16, 'segments': [0, 4], 'slope': -0.35, 'total_energy': 0.141667}
    assert request == before

def test_long_reference_gap():
    request = {'band': [0, 3], 'coherence_threshold': 0.5, 'energy_threshold': 0.01, 'max_gap': 1, 'min_coverage': 0.5, 'phase_limit': 3.141592653589793, 'ratio_threshold': 0, 'reference': [0, None, None, -1, 0, -1, 0, 1], 'sample_rate': 4, 'samples': [0, 1, 0, -1, 0, 1, 0, -1], 'segment_length': 4, 'step': 4}
    before = copy.deepcopy(request)
    assert run(request) == {'band_energy': 0.16, 'coherence': 1, 'coverage': 0.75, 'decision': 'alarm', 'phase': 3.141593, 'ratio': 1.0, 'reference_energy': 0.16, 'segments': [4], 'slope': -0.4, 'total_energy': 0.16}
    assert request == before

def test_paired_count_gate():
    request = {'band': [0, 3], 'coherence_threshold': 0.5, 'energy_threshold': 0.01, 'max_gap': 1, 'min_coverage': 0.5, 'min_segments': 2, 'phase_limit': 3.141592653589793, 'ratio_threshold': 0, 'reference': [0, 1, 0, -1, None, -1, 0, 1], 'sample_rate': 4, 'samples': [0, 1, 0, -1, 0, 1, 0, -1], 'segment_length': 4, 'step': 4}
    before = copy.deepcopy(request)
    assert run(request) == {'band_energy': None, 'coherence': None, 'coverage': 0.875, 'decision': 'insufficient_data', 'phase': None, 'ratio': None, 'reference_energy': None, 'segments': [0], 'slope': None, 'total_energy': None}
    assert request == before

def test_original_reference_coverage():
    request = {'band': [0, 3], 'coherence_threshold': 0.5, 'energy_threshold': 0.01, 'max_gap': 1, 'min_coverage': 0.8, 'phase_limit': 3.141592653589793, 'ratio_threshold': 0, 'reference': [0, None, 0, -1, 0, -1, 0, 1], 'sample_rate': 4, 'samples': [0, 1, 0, -1, 0, 1, 0, -1], 'segment_length': 4, 'step': 4}
    before = copy.deepcopy(request)
    assert run(request) == {'band_energy': 0.16, 'coherence': 1, 'coverage': 0.875, 'decision': 'alarm', 'phase': 3.141593, 'ratio': 1.0, 'reference_energy': 0.16, 'segments': [4], 'slope': -0.4, 'total_energy': 0.16}
    assert request == before

def test_nyquist_cross_energy():
    request = {'band': [2, 3], 'coherence_threshold': 0.5, 'energy_threshold': 0.01, 'max_gap': 1, 'min_coverage': 0.5, 'phase_limit': 3.141592653589793, 'ratio_threshold': 0, 'reference': [2, -2, 2, -2, 2, -2, 2, -2], 'sample_rate': 4, 'samples': [1, -1, 1, -1, 1, -1, 1, -1], 'segment_length': 4, 'step': 4}
    before = copy.deepcopy(request)
    assert run(request) == {'band_energy': 0.666667, 'coherence': 1, 'coverage': 1.0, 'decision': 'alarm', 'phase': 0.0, 'ratio': 0.543478, 'reference_energy': 2.666667, 'segments': [0, 4], 'slope': -0.4, 'total_energy': 1.226667}
    assert request == before

def test_zero_reference_power():
    request = {'band': [0, 3], 'coherence_threshold': 0.5, 'energy_threshold': 0.01, 'max_gap': 1, 'min_coverage': 0.5, 'phase_limit': 3.141592653589793, 'ratio_threshold': 0, 'reference': [0, 0, 0, 0, 0, 0, 0, 0], 'sample_rate': 4, 'samples': [0, 1, 0, -1, 0, 1, 0, -1], 'segment_length': 4, 'step': 4}
    before = copy.deepcopy(request)
    assert run(request) == {'band_energy': 0.16, 'coherence': 0.0, 'coverage': 1.0, 'decision': 'normal', 'phase': 0.0, 'ratio': 1.0, 'reference_energy': 0.0, 'segments': [0, 4], 'slope': -0.4, 'total_energy': 0.16}
    assert request == before

def test_both_zero_power():
    request = {'band': [0, 3], 'coherence_threshold': 0.5, 'energy_threshold': 0.01, 'max_gap': 1, 'min_coverage': 0.5, 'phase_limit': 3.141592653589793, 'ratio_threshold': 0, 'reference': [0, 0, 0, 0, 0, 0, 0, 0], 'sample_rate': 4, 'samples': [0, 0, 0, 0, 0, 0, 0, 0], 'segment_length': 4, 'step': 4}
    before = copy.deepcopy(request)
    assert run(request) == {'band_energy': 0.0, 'coherence': 0.0, 'coverage': 1.0, 'decision': 'normal', 'phase': 0.0, 'ratio': 0.0, 'reference_energy': 0.0, 'segments': [0, 4], 'slope': 0.0, 'total_energy': 0.0}
    assert request == before

def test_empty_bin_band():
    request = {'band': [0.1, 0.9], 'coherence_threshold': 0.5, 'energy_threshold': 0.01, 'max_gap': 1, 'min_coverage': 0.5, 'phase_limit': 3.141592653589793, 'ratio_threshold': 0, 'reference': [0, 1, 0, -1, 0, -1, 0, 1], 'sample_rate': 4, 'samples': [0, 1, 0, -1, 0, 1, 0, -1], 'segment_length': 4, 'step': 4}
    before = copy.deepcopy(request)
    assert run(request) == {'band_energy': 0.0, 'coherence': 0.0, 'coverage': 1.0, 'decision': 'normal', 'phase': 0.0, 'ratio': 0.0, 'reference_energy': 0.0, 'segments': [0, 4], 'slope': -0.4, 'total_energy': 0.16}
    assert request == before

def test_discard_partial_tail():
    request = {'band': [0, 3], 'coherence_threshold': 0.5, 'energy_threshold': 0.01, 'max_gap': 1, 'min_coverage': 0.5, 'phase_limit': 3.141592653589793, 'ratio_threshold': 0, 'reference': [0, 1, 0, -1, 0, -1, 0, 1, 5, 6], 'sample_rate': 4, 'samples': [0, 1, 0, -1, 0, 1, 0, -1, 3, 4], 'segment_length': 4, 'step': 4}
    before = copy.deepcopy(request)
    assert run(request) == {'band_energy': 0.16, 'coherence': 0.0, 'coverage': 1.0, 'decision': 'normal', 'phase': 0.0, 'ratio': 1.0, 'reference_energy': 0.16, 'segments': [0, 4], 'slope': -0.4, 'total_energy': 0.16}
    assert request == before

def test_phase_gate_uses_signed_cross():
    request = {'band': [0, 3], 'coherence_threshold': 0.5, 'energy_threshold': 0.01, 'max_gap': 1, 'min_coverage': 0.5, 'phase_limit': 0.1, 'ratio_threshold': 0, 'reference': [1, 0, -1, 0, 1, 0, -1, 0], 'sample_rate': 4, 'samples': [0, 1, 0, -1, 0, 1, 0, -1], 'segment_length': 4, 'step': 4}
    before = copy.deepcopy(request)
    assert run(request) == {'band_energy': 0.16, 'coherence': 0.605856, 'coverage': 1.0, 'decision': 'normal', 'phase': 2.485897, 'ratio': 1.0, 'reference_energy': 0.493333, 'segments': [0, 4], 'slope': -0.4, 'total_energy': 0.16}
    assert request == before

