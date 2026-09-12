import copy
import pytest
from fabops.domain import run


def test_campaign_and_overlap_cannot_rotate_model():
    request = {'cycles': [{'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 3], 'profile': [100, 100, 0, 130, 0]}, {'id': 'same_campaign', 'run': 'target-run', 'start': 6, 'end': 8, 'features': [100, -100], 'profile': [100, 100, 0, 130, 0]}, {'id': 'crossing_embargo', 'run': 'crossing_embargo', 'start': 7, 'end': 10, 'features': [-100, 100], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 6}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': [[1.0, 0.5], [0.5, 1.0]], 'score': 5.333333, 'decision': 'normal', 'calibration': [], 'threshold': 6}
    assert request == before

def test_stable_flag_zero_is_eligible():
    request = {'cycles': [{'id': 'transient', 'run': 'transient', 'start': 0, 'end': 1, 'features': [100, 100], 'profile': [100, 100, 0, 130, 1]}, {'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': [[1.0, 0.5], [0.5, 1.0]], 'score': 5.333333, 'decision': 'alarm', 'calibration': [], 'threshold': 5}
    assert request == before

def test_exclude_unhealthy_valve():
    request = {'cycles': [{'id': 'valve', 'run': 'valve', 'start': 0, 'end': 1, 'features': [100, 100], 'profile': [100, 90, 0, 130, 0]}, {'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': [[1.0, 0.5], [0.5, 1.0]], 'score': 5.333333, 'decision': 'alarm', 'calibration': [], 'threshold': 5}
    assert request == before

def test_exclude_unhealthy_pump():
    request = {'cycles': [{'id': 'pump', 'run': 'pump', 'start': 0, 'end': 1, 'features': [100, 100], 'profile': [100, 100, 1, 130, 0]}, {'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': [[1.0, 0.5], [0.5, 1.0]], 'score': 5.333333, 'decision': 'alarm', 'calibration': [], 'threshold': 5}
    assert request == before

def test_exclude_unhealthy_accumulator():
    request = {'cycles': [{'id': 'accumulator', 'run': 'accumulator', 'start': 0, 'end': 1, 'features': [100, 100], 'profile': [100, 100, 0, 115, 0]}, {'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': [[1.0, 0.5], [0.5, 1.0]], 'score': 5.333333, 'decision': 'alarm', 'calibration': [], 'threshold': 5}
    assert request == before

def test_exclude_unhealthy_cooler():
    request = {'cycles': [{'id': 'cooler', 'run': 'cooler', 'start': 0, 'end': 1, 'features': [100, 100], 'profile': [20, 100, 0, 130, 0]}, {'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': [[1.0, 0.5], [0.5, 1.0]], 'score': 5.333333, 'decision': 'alarm', 'calibration': [], 'threshold': 5}
    assert request == before

def test_future_features_do_not_fit():
    request = {'cycles': [{'id': 'future', 'run': 'future', 'start': 20, 'end': 21, 'features': [100, 100], 'profile': [100, 100, 0, 130, 0]}, {'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': [[1.0, 0.5], [0.5, 1.0]], 'score': 5.333333, 'decision': 'alarm', 'calibration': [], 'threshold': 5}
    assert request == before

def test_embargo_equality_is_allowed():
    request = {'cycles': [{'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 8, 'end': 9, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': [[1.0, 0.5], [0.5, 1.0]], 'score': 5.333333, 'decision': 'alarm', 'calibration': [], 'threshold': 5}
    assert request == before

def test_negative_correlation():
    request = {'cycles': [{'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, -2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, -1.0], 'scale': [1.0, 1.0], 'correlation': [[1.0, -0.5], [-0.5, 1.0]], 'score': 16.0, 'decision': 'alarm', 'calibration': [], 'threshold': 5}
    assert request == before

def test_full_shrinkage_is_identity():
    request = {'cycles': [{'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 3], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 1, 'threshold': 8}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': [[1.0, 0.0], [0.0, 1.0]], 'score': 8.0, 'decision': 'alarm', 'calibration': [], 'threshold': 8}
    assert request == before

def test_constant_coordinate_uses_unit_scale():
    request = {'cycles': [{'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 7], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 7], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 8], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 7.0], 'scale': [1.0, 1.0], 'correlation': [[1.0, 0.0], [0.0, 1.0]], 'score': 5.0, 'decision': 'alarm', 'calibration': [], 'threshold': 5}
    assert request == before

def test_population_scale_and_unrounded_scoring():
    request = {'cycles': [{'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [-2, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 1, 'end': 2, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'c', 'run': 'c', 'start': 2, 'end': 3, 'features': [2, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [2, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 3}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b', 'c'], 'center': [0.0, 0.0], 'scale': [1.632993, 1.0], 'correlation': [[1.0, 0.0], [0.0, 1.0]], 'score': 2.5, 'decision': 'normal', 'calibration': [], 'threshold': 3}
    assert request == before

def test_transient_target_is_deferred_after_fit():
    request = {'cycles': [{'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 1]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': [[1.0, 0.5], [0.5, 1.0]], 'score': None, 'decision': 'deferred', 'calibration': [], 'threshold': 5}
    assert request == before

def test_missing_target_is_deferred_after_fit():
    request = {'cycles': [{'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [None, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': [[1.0, 0.5], [0.5, 1.0]], 'score': None, 'decision': 'deferred', 'calibration': [], 'threshold': 5}
    assert request == before

def test_unhealthy_target_is_still_scored():
    request = {'cycles': [{'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [3, 73, 2, 90, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': [[1.0, 0.5], [0.5, 1.0]], 'score': 5.333333, 'decision': 'alarm', 'calibration': [], 'threshold': 5}
    assert request == before

def test_missing_training_is_excluded():
    request = {'cycles': [{'id': 'missing', 'run': 'missing', 'start': 0, 'end': 1, 'features': [None, 100], 'profile': [100, 100, 0, 130, 0]}, {'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': [[1.0, 0.5], [0.5, 1.0]], 'score': 5.333333, 'decision': 'alarm', 'calibration': [], 'threshold': 5}
    assert request == before

def test_empty_history():
    request = {'cycles': [{'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': [], 'center': None, 'scale': None, 'correlation': None, 'score': None, 'decision': 'insufficient_training', 'calibration': [], 'threshold': None}
    assert request == before

def test_one_training_cycle():
    request = {'cycles': [{'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a'], 'center': None, 'scale': None, 'correlation': None, 'score': None, 'decision': 'insufficient_training', 'calibration': [], 'threshold': None}
    assert request == before

def test_order_independent_selection():
    request = {'cycles': [{'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': [[1.0, 0.5], [0.5, 1.0]], 'score': 5.333333, 'decision': 'alarm', 'calibration': [], 'threshold': 5}
    assert request == before

def test_threshold_before_rounding():
    request = {'cycles': [{'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5.3333332}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': [[1.0, 0.5], [0.5, 1.0]], 'score': 5.333333, 'decision': 'alarm', 'calibration': [], 'threshold': 5.333333}
    assert request == before

def test_finite_sample_rank_0_1():
    request = {'alpha': 0.1, 'calibrate': True, 'cycles': [{'end': 1, 'features': [0, 0], 'id': 'a', 'profile': [100, 100, 0, 130, 0], 'run': 'old', 'start': 0}, {'end': 3, 'features': [2, 2], 'id': 'b', 'profile': [100, 100, 0, 130, 0], 'run': 'old', 'start': 2}, {'end': 5, 'features': [4, 0], 'id': 'c', 'profile': [100, 100, 0, 130, 0], 'run': 'new', 'start': 4}, {'end': 21, 'features': [3, 1], 'id': 't', 'profile': [100, 100, 0, 130, 0], 'run': 'target', 'start': 20}], 'embargo': 0, 'min_train': 2, 'shrinkage': 0.5, 'target': 't', 'threshold': 3}
    before = copy.deepcopy(request)
    assert run(request) == {'calibration': [['new', 17.333333]], 'center': [2.5, 0.5], 'correlation': [[1.0, -0.087039], [-0.087039, 1.0]], 'decision': 'insufficient_calibration', 'scale': [1.658312, 0.866025], 'score': 0.458015, 'threshold': None, 'training': ['a', 'b', 'c']}
    assert request == before

def test_finite_sample_rank_0_75():
    request = {'alpha': 0.75, 'calibrate': True, 'cycles': [{'end': 1, 'features': [0, 0], 'id': 'a', 'profile': [100, 100, 0, 130, 0], 'run': 'old', 'start': 0}, {'end': 3, 'features': [2, 2], 'id': 'b', 'profile': [100, 100, 0, 130, 0], 'run': 'old', 'start': 2}, {'end': 5, 'features': [4, 0], 'id': 'c', 'profile': [100, 100, 0, 130, 0], 'run': 'new', 'start': 4}, {'end': 21, 'features': [3, 1], 'id': 't', 'profile': [100, 100, 0, 130, 0], 'run': 'target', 'start': 20}], 'embargo': 0, 'min_train': 2, 'shrinkage': 0.5, 'target': 't', 'threshold': 3}
    before = copy.deepcopy(request)
    assert run(request) == {'calibration': [['new', 17.333333]], 'center': [2.5, 0.5], 'correlation': [[1.0, -0.087039], [-0.087039, 1.0]], 'decision': 'normal', 'scale': [1.658312, 0.866025], 'score': 0.458015, 'threshold': 17.333333, 'training': ['a', 'b', 'c']}
    assert request == before

def test_worst_member_per_run():
    request = {'alpha': 0.5, 'calibrate': True, 'cycles': [{'end': 1, 'features': [0, 0], 'id': 'a', 'profile': [100, 100, 0, 130, 0], 'run': 'old', 'start': 0}, {'end': 3, 'features': [2, 2], 'id': 'b', 'profile': [100, 100, 0, 130, 0], 'run': 'old', 'start': 2}, {'end': 5, 'features': [4, 0], 'id': 'c', 'profile': [100, 100, 0, 130, 0], 'run': 'new', 'start': 4}, {'end': 7, 'features': [9, 2], 'id': 'd', 'profile': [100, 100, 0, 130, 0], 'run': 'new', 'start': 6}, {'end': 21, 'features': [3, 1], 'id': 't', 'profile': [100, 100, 0, 130, 0], 'run': 'target', 'start': 20}], 'embargo': 0, 'min_train': 2, 'shrinkage': 0.5, 'target': 't', 'threshold': 3}
    before = copy.deepcopy(request)
    assert run(request) == {'calibration': [['new', 76.0]], 'center': [3.75, 1.0], 'correlation': [[1.0, 0.261602], [0.261602, 1.0]], 'decision': 'normal', 'scale': [3.344772, 1.0], 'score': 0.053973, 'threshold': 76.0, 'training': ['a', 'b', 'c', 'd']}
    assert request == before

def test_second_coordinate_only():
    request = {'cycles': [{'end': 1, 'features': [0, 0], 'id': 'a', 'profile': [100, 100, 0, 130, 0], 'run': 'old', 'start': 0}, {'end': 3, 'features': [2, 2], 'id': 'b', 'profile': [100, 100, 0, 130, 0], 'run': 'old', 'start': 2}, {'end': 5, 'features': [4, 0], 'id': 'c', 'profile': [100, 100, 0, 130, 0], 'run': 'new', 'start': 4}, {'end': 21, 'features': [None, 1], 'id': 't', 'profile': [100, 100, 0, 130, 0], 'run': 'target', 'start': 20}], 'embargo': 0, 'min_observed': 1, 'min_train': 2, 'shrinkage': 0.5, 'target': 't', 'threshold': 3}
    before = copy.deepcopy(request)
    assert run(request) == {'calibration': [], 'center': [2.5, 0.5], 'correlation': [[1.0, -0.087039], [-0.087039, 1.0]], 'decision': 'normal', 'scale': [1.658312, 0.866025], 'score': 0.666667, 'threshold': 3, 'training': ['a', 'b', 'c']}
    assert request == before

def test_no_observed_coordinate():
    request = {'cycles': [{'end': 1, 'features': [0, 0], 'id': 'a', 'profile': [100, 100, 0, 130, 0], 'run': 'old', 'start': 0}, {'end': 3, 'features': [2, 2], 'id': 'b', 'profile': [100, 100, 0, 130, 0], 'run': 'old', 'start': 2}, {'end': 5, 'features': [4, 0], 'id': 'c', 'profile': [100, 100, 0, 130, 0], 'run': 'new', 'start': 4}, {'end': 21, 'features': [None, None], 'id': 't', 'profile': [100, 100, 0, 130, 0], 'run': 'target', 'start': 20}], 'embargo': 0, 'min_observed': 1, 'min_train': 2, 'shrinkage': 0.5, 'target': 't', 'threshold': 3}
    before = copy.deepcopy(request)
    assert run(request) == {'calibration': [], 'center': [2.5, 0.5], 'correlation': [[1.0, -0.087039], [-0.087039, 1.0]], 'decision': 'deferred', 'scale': [1.658312, 0.866025], 'score': None, 'threshold': 3, 'training': ['a', 'b', 'c']}
    assert request == before

def test_calibration_embargo_removes_history():
    request = {'alpha': 0.5, 'calibrate': True, 'cycles': [{'end': 1, 'features': [0, 0], 'id': 'a', 'profile': [100, 100, 0, 130, 0], 'run': 'old', 'start': 0}, {'end': 3, 'features': [2, 2], 'id': 'b', 'profile': [100, 100, 0, 130, 0], 'run': 'old', 'start': 2}, {'end': 5, 'features': [4, 0], 'id': 'c', 'profile': [100, 100, 0, 130, 0], 'run': 'new', 'start': 4}, {'end': 21, 'features': [3, 1], 'id': 't', 'profile': [100, 100, 0, 130, 0], 'run': 'target', 'start': 20}], 'embargo': 2, 'min_train': 2, 'shrinkage': 0.5, 'target': 't', 'threshold': 3}
    before = copy.deepcopy(request)
    assert run(request) == {'calibration': [], 'center': [2.5, 0.5], 'correlation': [[1.0, -0.087039], [-0.087039, 1.0]], 'decision': 'insufficient_calibration', 'scale': [1.658312, 0.866025], 'score': 0.458015, 'threshold': None, 'training': ['a', 'b', 'c']}
    assert request == before

def test_dimension_1_calibration():
    request = {'alpha': 0.6, 'calibrate': True, 'cycles': [{'end': 1, 'features': [-1], 'id': 'p0', 'profile': [100, 100, 0, 130, 0], 'run': 'g0', 'start': 0}, {'end': 3, 'features': [1], 'id': 'p1', 'profile': [100, 100, 0, 130, 0], 'run': 'g0', 'start': 2}, {'end': 5, 'features': [3], 'id': 'p2', 'profile': [100, 100, 0, 130, 0], 'run': 'g1', 'start': 4}, {'end': 7, 'features': [-2], 'id': 'p3', 'profile': [100, 100, 0, 130, 0], 'run': 'g1', 'start': 6}, {'end': 9, 'features': [0], 'id': 'p4', 'profile': [100, 100, 0, 130, 0], 'run': 'g2', 'start': 8}, {'end': 11, 'features': [2], 'id': 'p5', 'profile': [100, 100, 0, 130, 0], 'run': 'g2', 'start': 10}, {'end': 13, 'features': [-3], 'id': 'p6', 'profile': [100, 100, 0, 130, 0], 'run': 'g3', 'start': 12}, {'end': 15, 'features': [-1], 'id': 'p7', 'profile': [100, 100, 0, 130, 0], 'run': 'g3', 'start': 14}, {'end': 31, 'features': [2], 'id': 't', 'profile': [100, 100, 0, 130, 0], 'run': 'target', 'start': 30}], 'embargo': 0, 'min_train': 2, 'shrinkage': 0.2, 'target': 't', 'threshold': 3}
    before = copy.deepcopy(request)
    assert run(request) == {'calibration': [['g1', 9.0], ['g2', 0.830508], ['g3', 4.2]], 'center': [-0.125], 'correlation': [[1.0]], 'decision': 'normal', 'scale': [1.899836], 'score': 1.251082, 'threshold': 4.2, 'training': ['p0', 'p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7']}
    assert request == before

def test_dimension_3_calibration():
    request = {'alpha': 0.6, 'calibrate': True, 'cycles': [{'end': 1, 'features': [-1, 0, 1], 'id': 'p0', 'profile': [100, 100, 0, 130, 0], 'run': 'g0', 'start': 0}, {'end': 3, 'features': [1, 3, -2], 'id': 'p1', 'profile': [100, 100, 0, 130, 0], 'run': 'g0', 'start': 2}, {'end': 5, 'features': [3, -1, 2], 'id': 'p2', 'profile': [100, 100, 0, 130, 0], 'run': 'g1', 'start': 4}, {'end': 7, 'features': [-2, 2, -1], 'id': 'p3', 'profile': [100, 100, 0, 130, 0], 'run': 'g1', 'start': 6}, {'end': 9, 'features': [0, -2, 3], 'id': 'p4', 'profile': [100, 100, 0, 130, 0], 'run': 'g2', 'start': 8}, {'end': 11, 'features': [2, 1, 0], 'id': 'p5', 'profile': [100, 100, 0, 130, 0], 'run': 'g2', 'start': 10}, {'end': 13, 'features': [-3, -3, -3], 'id': 'p6', 'profile': [100, 100, 0, 130, 0], 'run': 'g3', 'start': 12}, {'end': 15, 'features': [-1, 0, 1], 'id': 'p7', 'profile': [100, 100, 0, 130, 0], 'run': 'g3', 'start': 14}, {'end': 31, 'features': [2, 2, 2], 'id': 't', 'profile': [100, 100, 0, 130, 0], 'run': 'target', 'start': 30}], 'embargo': 0, 'min_train': 2, 'shrinkage': 0.2, 'target': 't', 'threshold': 3}
    before = copy.deepcopy(request)
    assert run(request) == {'calibration': [['g1', 72.606838], ['g2', 4.773019], ['g3', 46.322964]], 'center': [-0.125, 0.0, 0.125], 'correlation': [[1.0, 0.196946, 0.363636], [0.196946, 1.0, -0.196946], [0.363636, -0.196946, 1.0]], 'decision': 'normal', 'scale': [1.899836, 1.870829, 1.899836], 'score': 2.843246, 'threshold': 46.322964, 'training': ['p0', 'p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7']}
    assert request == before

def test_dimension_3_missing():
    request = {'alpha': 0.6, 'calibrate': True, 'cycles': [{'end': 1, 'features': [-1, 0, 1], 'id': 'p0', 'profile': [100, 100, 0, 130, 0], 'run': 'g0', 'start': 0}, {'end': 3, 'features': [1, 3, -2], 'id': 'p1', 'profile': [100, 100, 0, 130, 0], 'run': 'g0', 'start': 2}, {'end': 5, 'features': [3, -1, 2], 'id': 'p2', 'profile': [100, 100, 0, 130, 0], 'run': 'g1', 'start': 4}, {'end': 7, 'features': [-2, 2, -1], 'id': 'p3', 'profile': [100, 100, 0, 130, 0], 'run': 'g1', 'start': 6}, {'end': 9, 'features': [0, -2, 3], 'id': 'p4', 'profile': [100, 100, 0, 130, 0], 'run': 'g2', 'start': 8}, {'end': 11, 'features': [2, 1, 0], 'id': 'p5', 'profile': [100, 100, 0, 130, 0], 'run': 'g2', 'start': 10}, {'end': 13, 'features': [-3, -3, -3], 'id': 'p6', 'profile': [100, 100, 0, 130, 0], 'run': 'g3', 'start': 12}, {'end': 15, 'features': [-1, 0, 1], 'id': 'p7', 'profile': [100, 100, 0, 130, 0], 'run': 'g3', 'start': 14}, {'end': 31, 'features': [2, None, 2], 'id': 't', 'profile': [100, 100, 0, 130, 0], 'run': 'target', 'start': 30}], 'embargo': 0, 'min_observed': 1, 'min_train': 2, 'shrinkage': 0.2, 'target': 't', 'threshold': 3}
    before = copy.deepcopy(request)
    assert run(request) == {'calibration': [['g1', 72.606838], ['g2', 4.773019], ['g3', 46.322964]], 'center': [-0.125, 0.0, 0.125], 'correlation': [[1.0, 0.196946, 0.363636], [0.196946, 1.0, -0.196946], [0.363636, -0.196946, 1.0]], 'decision': 'normal', 'scale': [1.899836, 1.870829, 1.899836], 'score': 2.458503, 'threshold': 46.322964, 'training': ['p0', 'p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7']}
    assert request == before

def test_dimension_4_calibration():
    request = {'alpha': 0.6, 'calibrate': True, 'cycles': [{'end': 1, 'features': [-1, 0, 1, 2], 'id': 'p0', 'profile': [100, 100, 0, 130, 0], 'run': 'g0', 'start': 0}, {'end': 3, 'features': [1, 3, -2, 0], 'id': 'p1', 'profile': [100, 100, 0, 130, 0], 'run': 'g0', 'start': 2}, {'end': 5, 'features': [3, -1, 2, -2], 'id': 'p2', 'profile': [100, 100, 0, 130, 0], 'run': 'g1', 'start': 4}, {'end': 7, 'features': [-2, 2, -1, 3], 'id': 'p3', 'profile': [100, 100, 0, 130, 0], 'run': 'g1', 'start': 6}, {'end': 9, 'features': [0, -2, 3, 1], 'id': 'p4', 'profile': [100, 100, 0, 130, 0], 'run': 'g2', 'start': 8}, {'end': 11, 'features': [2, 1, 0, -1], 'id': 'p5', 'profile': [100, 100, 0, 130, 0], 'run': 'g2', 'start': 10}, {'end': 13, 'features': [-3, -3, -3, -3], 'id': 'p6', 'profile': [100, 100, 0, 130, 0], 'run': 'g3', 'start': 12}, {'end': 15, 'features': [-1, 0, 1, 2], 'id': 'p7', 'profile': [100, 100, 0, 130, 0], 'run': 'g3', 'start': 14}, {'end': 31, 'features': [2, 2, 2, 2], 'id': 't', 'profile': [100, 100, 0, 130, 0], 'run': 'target', 'start': 30}], 'embargo': 0, 'min_train': 2, 'shrinkage': 0.2, 'target': 't', 'threshold': 3}
    before = copy.deepcopy(request)
    assert run(request) == {'calibration': [['g1', 109.411765], ['g2', 4.872191], ['g3', 84.0]], 'center': [-0.125, 0.0, 0.125, 0.25], 'correlation': [[1.0, 0.196946, 0.363636, -0.232104], [0.196946, 1.0, -0.196946, 0.377124], [0.363636, -0.196946, 1.0, 0.232104], [-0.232104, 0.377124, 0.232104, 1.0]], 'decision': 'normal', 'scale': [1.899836, 1.870829, 1.899836, 1.984313], 'score': 3.039518, 'threshold': 84.0, 'training': ['p0', 'p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7']}
    assert request == before

def test_dimension_4_missing():
    request = {'alpha': 0.6, 'calibrate': True, 'cycles': [{'end': 1, 'features': [-1, 0, 1, 2], 'id': 'p0', 'profile': [100, 100, 0, 130, 0], 'run': 'g0', 'start': 0}, {'end': 3, 'features': [1, 3, -2, 0], 'id': 'p1', 'profile': [100, 100, 0, 130, 0], 'run': 'g0', 'start': 2}, {'end': 5, 'features': [3, -1, 2, -2], 'id': 'p2', 'profile': [100, 100, 0, 130, 0], 'run': 'g1', 'start': 4}, {'end': 7, 'features': [-2, 2, -1, 3], 'id': 'p3', 'profile': [100, 100, 0, 130, 0], 'run': 'g1', 'start': 6}, {'end': 9, 'features': [0, -2, 3, 1], 'id': 'p4', 'profile': [100, 100, 0, 130, 0], 'run': 'g2', 'start': 8}, {'end': 11, 'features': [2, 1, 0, -1], 'id': 'p5', 'profile': [100, 100, 0, 130, 0], 'run': 'g2', 'start': 10}, {'end': 13, 'features': [-3, -3, -3, -3], 'id': 'p6', 'profile': [100, 100, 0, 130, 0], 'run': 'g3', 'start': 12}, {'end': 15, 'features': [-1, 0, 1, 2], 'id': 'p7', 'profile': [100, 100, 0, 130, 0], 'run': 'g3', 'start': 14}, {'end': 31, 'features': [2, None, 2, 2], 'id': 't', 'profile': [100, 100, 0, 130, 0], 'run': 'target', 'start': 30}], 'embargo': 0, 'min_observed': 1, 'min_train': 2, 'shrinkage': 0.2, 'target': 't', 'threshold': 3}
    before = copy.deepcopy(request)
    assert run(request) == {'calibration': [['g1', 109.411765], ['g2', 4.872191], ['g3', 84.0]], 'center': [-0.125, 0.0, 0.125, 0.25], 'correlation': [[1.0, 0.196946, 0.363636, -0.232104], [0.196946, 1.0, -0.196946, 0.377124], [0.363636, -0.196946, 1.0, 0.232104], [-0.232104, 0.377124, 0.232104, 1.0]], 'decision': 'normal', 'scale': [1.899836, 1.870829, 1.899836, 1.984313], 'score': 3.573323, 'threshold': 84.0, 'training': ['p0', 'p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7']}
    assert request == before

def test_dimension_5_calibration():
    request = {'alpha': 0.6, 'calibrate': True, 'cycles': [{'end': 1, 'features': [-1, 0, 1, 2, 3], 'id': 'p0', 'profile': [100, 100, 0, 130, 0], 'run': 'g0', 'start': 0}, {'end': 3, 'features': [1, 3, -2, 0, 2], 'id': 'p1', 'profile': [100, 100, 0, 130, 0], 'run': 'g0', 'start': 2}, {'end': 5, 'features': [3, -1, 2, -2, 1], 'id': 'p2', 'profile': [100, 100, 0, 130, 0], 'run': 'g1', 'start': 4}, {'end': 7, 'features': [-2, 2, -1, 3, 0], 'id': 'p3', 'profile': [100, 100, 0, 130, 0], 'run': 'g1', 'start': 6}, {'end': 9, 'features': [0, -2, 3, 1, -1], 'id': 'p4', 'profile': [100, 100, 0, 130, 0], 'run': 'g2', 'start': 8}, {'end': 11, 'features': [2, 1, 0, -1, -2], 'id': 'p5', 'profile': [100, 100, 0, 130, 0], 'run': 'g2', 'start': 10}, {'end': 13, 'features': [-3, -3, -3, -3, -3], 'id': 'p6', 'profile': [100, 100, 0, 130, 0], 'run': 'g3', 'start': 12}, {'end': 15, 'features': [-1, 0, 1, 2, 3], 'id': 'p7', 'profile': [100, 100, 0, 130, 0], 'run': 'g3', 'start': 14}, {'end': 31, 'features': [2, 2, 2, 2, 2], 'id': 't', 'profile': [100, 100, 0, 130, 0], 'run': 'target', 'start': 30}], 'embargo': 0, 'min_train': 2, 'shrinkage': 0.2, 'target': 't', 'threshold': 3}
    before = copy.deepcopy(request)
    assert run(request) == {'calibration': [['g1', 163.465608], ['g2', 11.056855], ['g3', 88.413164]], 'center': [-0.125, 0.0, 0.125, 0.25, 0.375], 'correlation': [[1.0, 0.196946, 0.363636, -0.232104, 0.108745], [0.196946, 1.0, -0.196946, 0.377124, 0.353381], [0.363636, -0.196946, 1.0, 0.232104, 0.23924], [-0.232104, 0.377124, 0.232104, 1.0, 0.45811], [0.108745, 0.353381, 0.23924, 0.45811, 1.0]], 'decision': 'normal', 'scale': [1.899836, 1.870829, 1.899836, 1.984313, 2.117634], 'score': 3.044196, 'threshold': 88.413164, 'training': ['p0', 'p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7']}
    assert request == before

def test_dimension_5_missing():
    request = {'alpha': 0.6, 'calibrate': True, 'cycles': [{'end': 1, 'features': [-1, 0, 1, 2, 3], 'id': 'p0', 'profile': [100, 100, 0, 130, 0], 'run': 'g0', 'start': 0}, {'end': 3, 'features': [1, 3, -2, 0, 2], 'id': 'p1', 'profile': [100, 100, 0, 130, 0], 'run': 'g0', 'start': 2}, {'end': 5, 'features': [3, -1, 2, -2, 1], 'id': 'p2', 'profile': [100, 100, 0, 130, 0], 'run': 'g1', 'start': 4}, {'end': 7, 'features': [-2, 2, -1, 3, 0], 'id': 'p3', 'profile': [100, 100, 0, 130, 0], 'run': 'g1', 'start': 6}, {'end': 9, 'features': [0, -2, 3, 1, -1], 'id': 'p4', 'profile': [100, 100, 0, 130, 0], 'run': 'g2', 'start': 8}, {'end': 11, 'features': [2, 1, 0, -1, -2], 'id': 'p5', 'profile': [100, 100, 0, 130, 0], 'run': 'g2', 'start': 10}, {'end': 13, 'features': [-3, -3, -3, -3, -3], 'id': 'p6', 'profile': [100, 100, 0, 130, 0], 'run': 'g3', 'start': 12}, {'end': 15, 'features': [-1, 0, 1, 2, 3], 'id': 'p7', 'profile': [100, 100, 0, 130, 0], 'run': 'g3', 'start': 14}, {'end': 31, 'features': [2, None, 2, 2, 2], 'id': 't', 'profile': [100, 100, 0, 130, 0], 'run': 'target', 'start': 30}], 'embargo': 0, 'min_observed': 1, 'min_train': 2, 'shrinkage': 0.2, 'target': 't', 'threshold': 3}
    before = copy.deepcopy(request)
    assert run(request) == {'calibration': [['g1', 163.465608], ['g2', 11.056855], ['g3', 88.413164]], 'center': [-0.125, 0.0, 0.125, 0.25, 0.375], 'correlation': [[1.0, 0.196946, 0.363636, -0.232104, 0.108745], [0.196946, 1.0, -0.196946, 0.377124, 0.353381], [0.363636, -0.196946, 1.0, 0.232104, 0.23924], [-0.232104, 0.377124, 0.232104, 1.0, 0.45811], [0.108745, 0.353381, 0.23924, 0.45811, 1.0]], 'decision': 'normal', 'scale': [1.899836, 1.870829, 1.899836, 1.984313, 2.117634], 'score': 3.354679, 'threshold': 88.413164, 'training': ['p0', 'p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7']}
    assert request == before

