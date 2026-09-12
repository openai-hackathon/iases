import copy
import pytest
from fabops.domain import run


def test_constant_units_and_publication():
    request = {'samples': [{'id': 'p0', 'channel': 'pressure', 't': '0', 'raw': '600', 'revision': 1, 'recorded': 0, 'epoch': 'e', 'valid': True, 'deleted': False}, {'id': 'p2', 'channel': 'pressure', 't': '2', 'raw': '600', 'revision': 1, 'recorded': 0, 'epoch': 'e', 'valid': True, 'deleted': False}, {'id': 'q0', 'channel': 'flow', 't': '0', 'raw': '60', 'revision': 1, 'recorded': 0, 'epoch': 'e', 'valid': True, 'deleted': False}, {'id': 'q2', 'channel': 'flow', 't': '2', 'raw': '60', 'revision': 1, 'recorded': 0, 'epoch': 'e', 'valid': True, 'deleted': False}], 'calibrations': [{'id': 'pressure', 'channel': 'pressure', 'start': '-100', 'end': '100', 'gain': '1', 'offset': '0', 'revision': 1, 'recorded': 0, 'deleted': False}, {'id': 'flow', 'channel': 'flow', 'start': '-100', 'end': '100', 'gain': '1', 'offset': '0', 'revision': 1, 'recorded': 0, 'deleted': False}], 'clocks': [{'channel': 'pressure', 'epoch': 'e', 'local_origin': '0', 'global_origin': '0', 'rate': '1'}, {'channel': 'flow', 'epoch': 'e', 'local_origin': '0', 'global_origin': '0', 'rate': '1'}], 'windows': [{'id': 'w', 'start': '0', 'end': '2'}], 'queries': [1], 'max_gap': {'pressure': '3', 'flow': '3'}, 'min_coverage': '1'}
    before = copy.deepcopy(request)
    assert run(request) == [{'windows': [{'id': 'w', 'coverage': '1', 'accepted': True, 'volume': '2', 'work': '120'}], 'changes': [{'op': 'upsert', 'value': {'id': 'w', 'coverage': '1', 'accepted': True, 'volume': '2', 'work': '120'}}]}]
    assert request == before

def test_joint_linear_product():
    request = {'samples': [{'id': 'p0', 'channel': 'pressure', 't': '0', 'raw': '0', 'revision': 1, 'recorded': 0, 'epoch': 'e', 'valid': True, 'deleted': False}, {'id': 'p2', 'channel': 'pressure', 't': '2', 'raw': '600', 'revision': 1, 'recorded': 0, 'epoch': 'e', 'valid': True, 'deleted': False}, {'id': 'q0', 'channel': 'flow', 't': '0', 'raw': '0', 'revision': 1, 'recorded': 0, 'epoch': 'e', 'valid': True, 'deleted': False}, {'id': 'q2', 'channel': 'flow', 't': '2', 'raw': '60', 'revision': 1, 'recorded': 0, 'epoch': 'e', 'valid': True, 'deleted': False}], 'calibrations': [{'id': 'pressure', 'channel': 'pressure', 'start': '-100', 'end': '100', 'gain': '1', 'offset': '0', 'revision': 1, 'recorded': 0, 'deleted': False}, {'id': 'flow', 'channel': 'flow', 'start': '-100', 'end': '100', 'gain': '1', 'offset': '0', 'revision': 1, 'recorded': 0, 'deleted': False}], 'clocks': [{'channel': 'pressure', 'epoch': 'e', 'local_origin': '0', 'global_origin': '0', 'rate': '1'}, {'channel': 'flow', 'epoch': 'e', 'local_origin': '0', 'global_origin': '0', 'rate': '1'}], 'windows': [{'id': 'w', 'start': '0', 'end': '2'}], 'queries': [1], 'max_gap': {'pressure': '3', 'flow': '3'}, 'min_coverage': '1'}
    before = copy.deepcopy(request)
    assert run(request) == [{'windows': [{'id': 'w', 'coverage': '1', 'accepted': True, 'volume': '1', 'work': '40'}], 'changes': [{'op': 'upsert', 'value': {'id': 'w', 'coverage': '1', 'accepted': True, 'volume': '1', 'work': '40'}}]}]
    assert request == before

def test_late_raw_correction_retracts():
    request = {'samples': [{'id': 'p0', 'channel': 'pressure', 't': '0', 'raw': '600', 'revision': 1, 'recorded': 0, 'epoch': 'e', 'valid': True, 'deleted': False}, {'id': 'p2', 'channel': 'pressure', 't': '2', 'raw': '600', 'revision': 1, 'recorded': 0, 'epoch': 'e', 'valid': True, 'deleted': False}, {'id': 'q0', 'channel': 'flow', 't': '0', 'raw': '60', 'revision': 1, 'recorded': 0, 'epoch': 'e', 'valid': True, 'deleted': False}, {'id': 'q2', 'channel': 'flow', 't': '2', 'raw': '60', 'revision': 1, 'recorded': 0, 'epoch': 'e', 'valid': True, 'deleted': False}, {'id': 'q2', 'channel': 'flow', 't': '2', 'raw': '120', 'revision': 2, 'recorded': 5, 'epoch': 'e', 'valid': True, 'deleted': False}], 'calibrations': [{'id': 'pressure', 'channel': 'pressure', 'start': '-100', 'end': '100', 'gain': '1', 'offset': '0', 'revision': 1, 'recorded': 0, 'deleted': False}, {'id': 'flow', 'channel': 'flow', 'start': '-100', 'end': '100', 'gain': '1', 'offset': '0', 'revision': 1, 'recorded': 0, 'deleted': False}], 'clocks': [{'channel': 'pressure', 'epoch': 'e', 'local_origin': '0', 'global_origin': '0', 'rate': '1'}, {'channel': 'flow', 'epoch': 'e', 'local_origin': '0', 'global_origin': '0', 'rate': '1'}], 'windows': [{'id': 'w', 'start': '0', 'end': '2'}], 'queries': [1, 5], 'max_gap': {'pressure': '3', 'flow': '3'}, 'min_coverage': '1'}
    before = copy.deepcopy(request)
    assert run(request) == [{'windows': [{'id': 'w', 'coverage': '1', 'accepted': True, 'volume': '2', 'work': '120'}], 'changes': [{'op': 'upsert', 'value': {'id': 'w', 'coverage': '1', 'accepted': True, 'volume': '2', 'work': '120'}}]}, {'windows': [{'id': 'w', 'coverage': '1', 'accepted': True, 'volume': '3', 'work': '180'}], 'changes': [{'op': 'retract', 'value': {'id': 'w', 'coverage': '1', 'accepted': True, 'volume': '2', 'work': '120'}}, {'op': 'upsert', 'value': {'id': 'w', 'coverage': '1', 'accepted': True, 'volume': '3', 'work': '180'}}]}]
    assert request == before

def test_calibration_step_inside_support():
    request = {'samples': [{'id': 'p0', 'channel': 'pressure', 't': '0', 'raw': '600', 'revision': 1, 'recorded': 0, 'epoch': 'e', 'valid': True, 'deleted': False}, {'id': 'p2', 'channel': 'pressure', 't': '2', 'raw': '600', 'revision': 1, 'recorded': 0, 'epoch': 'e', 'valid': True, 'deleted': False}, {'id': 'q0', 'channel': 'flow', 't': '0', 'raw': '60', 'revision': 1, 'recorded': 0, 'epoch': 'e', 'valid': True, 'deleted': False}, {'id': 'q2', 'channel': 'flow', 't': '2', 'raw': '60', 'revision': 1, 'recorded': 0, 'epoch': 'e', 'valid': True, 'deleted': False}], 'calibrations': [{'id': 'a', 'channel': 'pressure', 'start': '-100', 'end': '1', 'gain': '1', 'offset': '0', 'revision': 1, 'recorded': 0, 'deleted': False}, {'id': 'b', 'channel': 'pressure', 'start': '1', 'end': '100', 'gain': '2', 'offset': '0', 'revision': 1, 'recorded': 0, 'deleted': False}, {'id': 'flow', 'channel': 'flow', 'start': '-100', 'end': '100', 'gain': '1', 'offset': '0', 'revision': 1, 'recorded': 0, 'deleted': False}], 'clocks': [{'channel': 'pressure', 'epoch': 'e', 'local_origin': '0', 'global_origin': '0', 'rate': '1'}, {'channel': 'flow', 'epoch': 'e', 'local_origin': '0', 'global_origin': '0', 'rate': '1'}], 'windows': [{'id': 'w', 'start': '0', 'end': '2'}], 'queries': [1], 'max_gap': {'pressure': '3', 'flow': '3'}, 'min_coverage': '1'}
    before = copy.deepcopy(request)
    assert run(request) == [{'windows': [{'id': 'w', 'coverage': '1', 'accepted': True, 'volume': '2', 'work': '180'}], 'changes': [{'op': 'upsert', 'value': {'id': 'w', 'coverage': '1', 'accepted': True, 'volume': '2', 'work': '180'}}]}]
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
