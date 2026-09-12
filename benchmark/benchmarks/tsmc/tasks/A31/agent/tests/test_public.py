import copy
import pytest
from fabops.domain import run


def test_constant_trace():
    request = {'samples': [2, 2, 2, 2], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 0.0, 'band_energy': 0.0, 'total_energy': 0.0, 'ratio': 0.0, 'decision': 'normal', 'segments': [0], 'reference_energy': 0.0, 'coherence': 0.0, 'phase': 0.0}
    assert request == before

def test_periodic_band_energy():
    request = {'samples': [1, -1, -1, 1], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 0.0, 'band_energy': 0.666667, 'total_energy': 1.0, 'ratio': 0.666667, 'decision': 'alarm', 'segments': [0], 'reference_energy': 0.666667, 'coherence': 1.0, 'phase': 0.0}
    assert request == before

def test_remove_trend_before_window():
    request = {'samples': [1, 1, 3, 7], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 2.0, 'band_energy': 0.666667, 'total_energy': 1.0, 'ratio': 0.666667, 'decision': 'alarm', 'segments': [0], 'reference_energy': 0.666667, 'coherence': 1.0, 'phase': 0.0}
    assert request == before

def test_imputation_cannot_raise_coverage():
    request = {'samples': [1, None, -1, 1], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0.8, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 0.75, 'slope': None, 'band_energy': None, 'total_energy': None, 'ratio': None, 'decision': 'insufficient_data', 'segments': [], 'reference_energy': None, 'coherence': None, 'phase': None}
    assert request == before

def test_opposite_windows_cancel_cross_spectrum():
    request = {'band': [0, 3], 'coherence_threshold': 0.5, 'energy_threshold': 0.01, 'max_gap': 1, 'min_coverage': 0.5, 'phase_limit': 3.141592653589793, 'ratio_threshold': 0, 'reference': [0, 1, 0, -1, 0, -1, 0, 1], 'sample_rate': 4, 'samples': [0, 1, 0, -1, 0, 1, 0, -1], 'segment_length': 4, 'step': 4}
    before = copy.deepcopy(request)
    assert run(request) == {'band_energy': 0.16, 'coherence': 0.0, 'coverage': 1.0, 'decision': 'normal', 'phase': 0.0, 'ratio': 1.0, 'reference_energy': 0.16, 'segments': [0, 4], 'slope': -0.4, 'total_energy': 0.16}
    assert request == before

def test_signed_phase_0():
    request = {'band': [0, 3], 'coherence_threshold': 0.5, 'energy_threshold': 0.01, 'max_gap': 1, 'min_coverage': 0.5, 'phase_limit': 3.141592653589793, 'ratio_threshold': 0, 'reference': [1, 0, -1, 0, 1, 0, -1, 0], 'sample_rate': 4, 'samples': [0, 1, 0, -1, 0, 1, 0, -1], 'segment_length': 4, 'step': 4}
    before = copy.deepcopy(request)
    assert run(request) == {'band_energy': 0.16, 'coherence': 0.605856, 'coverage': 1.0, 'decision': 'alarm', 'phase': 2.485897, 'ratio': 1.0, 'reference_energy': 0.493333, 'segments': [0, 4], 'slope': -0.4, 'total_energy': 0.16}
    assert request == before

def test_overlap_changes_ensemble():
    request = {'band': [0, 3], 'coherence_threshold': 0.5, 'energy_threshold': 0.01, 'max_gap': 1, 'min_coverage': 0.5, 'phase_limit': 3.141592653589793, 'ratio_threshold': 0, 'reference': [0, 1, 0, -1, 0, -1, 0, 1], 'sample_rate': 4, 'samples': [0, 1, 0, -1, 0, 1, 0, -1], 'segment_length': 4, 'step': 2}
    before = copy.deepcopy(request)
    assert run(request) == {'band_energy': 0.16, 'coherence': 0.059693, 'coverage': 1.0, 'decision': 'normal', 'phase': 1.670465, 'ratio': 1.0, 'reference_energy': 0.208889, 'segments': [0, 2, 4], 'slope': -0.133333, 'total_energy': 0.16}
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
