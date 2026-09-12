import copy
import pytest
from fabops.domain import run


def test_constant_trace():
    request = {'samples': [2, 2, 2, 2], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 0.0, 'band_energy': 0.0, 'total_energy': 0.0, 'ratio': 0.0, 'decision': 'normal'}
    assert request == before

def test_periodic_band_energy():
    request = {'samples': [1, -1, -1, 1], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 0.0, 'band_energy': 0.666667, 'total_energy': 1.0, 'ratio': 0.666667, 'decision': 'alarm'}
    assert request == before

def test_remove_trend_before_window():
    request = {'samples': [1, 1, 3, 7], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0.75, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 1.0, 'slope': 2.0, 'band_energy': 0.666667, 'total_energy': 1.0, 'ratio': 0.666667, 'decision': 'alarm'}
    assert request == before

def test_imputation_cannot_raise_coverage():
    request = {'samples': [1, None, -1, 1], 'sample_rate': 4, 'band': [1, 2], 'max_gap': 1, 'min_coverage': 0.8, 'energy_threshold': 0.5, 'ratio_threshold': 0.6}
    before = copy.deepcopy(request)
    assert run(request) == {'coverage': 0.75, 'slope': None, 'band_energy': None, 'total_energy': None, 'ratio': None, 'decision': 'insufficient_data'}
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
