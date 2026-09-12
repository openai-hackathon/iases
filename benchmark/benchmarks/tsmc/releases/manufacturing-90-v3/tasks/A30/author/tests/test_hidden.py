import copy
import pytest
from fabops.domain import run


def test_campaign_and_overlap_cannot_rotate_model():
    request = {'cycles': [{'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 3], 'profile': [100, 100, 0, 130, 0]}, {'id': 'same_campaign', 'run': 'target-run', 'start': 6, 'end': 8, 'features': [100, -100], 'profile': [100, 100, 0, 130, 0]}, {'id': 'crossing_embargo', 'run': 'crossing_embargo', 'start': 7, 'end': 10, 'features': [-100, 100], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 6}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': 0.5, 'score': 5.333333, 'decision': 'normal'}
    assert request == before

def test_stable_flag_zero_is_eligible():
    request = {'cycles': [{'id': 'transient', 'run': 'transient', 'start': 0, 'end': 1, 'features': [100, 100], 'profile': [100, 100, 0, 130, 1]}, {'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': 0.5, 'score': 5.333333, 'decision': 'alarm'}
    assert request == before

def test_exclude_unhealthy_valve():
    request = {'cycles': [{'id': 'valve', 'run': 'valve', 'start': 0, 'end': 1, 'features': [100, 100], 'profile': [100, 90, 0, 130, 0]}, {'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': 0.5, 'score': 5.333333, 'decision': 'alarm'}
    assert request == before

def test_exclude_unhealthy_pump():
    request = {'cycles': [{'id': 'pump', 'run': 'pump', 'start': 0, 'end': 1, 'features': [100, 100], 'profile': [100, 100, 1, 130, 0]}, {'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': 0.5, 'score': 5.333333, 'decision': 'alarm'}
    assert request == before

def test_exclude_unhealthy_accumulator():
    request = {'cycles': [{'id': 'accumulator', 'run': 'accumulator', 'start': 0, 'end': 1, 'features': [100, 100], 'profile': [100, 100, 0, 115, 0]}, {'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': 0.5, 'score': 5.333333, 'decision': 'alarm'}
    assert request == before

def test_exclude_unhealthy_cooler():
    request = {'cycles': [{'id': 'cooler', 'run': 'cooler', 'start': 0, 'end': 1, 'features': [100, 100], 'profile': [20, 100, 0, 130, 0]}, {'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': 0.5, 'score': 5.333333, 'decision': 'alarm'}
    assert request == before

def test_future_features_do_not_fit():
    request = {'cycles': [{'id': 'future', 'run': 'future', 'start': 20, 'end': 21, 'features': [100, 100], 'profile': [100, 100, 0, 130, 0]}, {'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': 0.5, 'score': 5.333333, 'decision': 'alarm'}
    assert request == before

def test_embargo_equality_is_allowed():
    request = {'cycles': [{'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 8, 'end': 9, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': 0.5, 'score': 5.333333, 'decision': 'alarm'}
    assert request == before

def test_negative_correlation():
    request = {'cycles': [{'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, -2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, -1.0], 'scale': [1.0, 1.0], 'correlation': -0.5, 'score': 16.0, 'decision': 'alarm'}
    assert request == before

def test_full_shrinkage_is_identity():
    request = {'cycles': [{'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 3], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 1, 'threshold': 8}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': 0.0, 'score': 8.0, 'decision': 'alarm'}
    assert request == before

def test_constant_coordinate_uses_unit_scale():
    request = {'cycles': [{'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 7], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 7], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 8], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 7.0], 'scale': [1.0, 1.0], 'correlation': 0.0, 'score': 5.0, 'decision': 'alarm'}
    assert request == before

def test_population_scale_and_unrounded_scoring():
    request = {'cycles': [{'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [-2, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 1, 'end': 2, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'c', 'run': 'c', 'start': 2, 'end': 3, 'features': [2, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [2, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 3}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b', 'c'], 'center': [0.0, 0.0], 'scale': [1.632993, 1.0], 'correlation': 0.0, 'score': 2.5, 'decision': 'normal'}
    assert request == before

def test_transient_target_is_deferred_after_fit():
    request = {'cycles': [{'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 1]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': 0.5, 'score': None, 'decision': 'deferred'}
    assert request == before

def test_missing_target_is_deferred_after_fit():
    request = {'cycles': [{'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [None, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': 0.5, 'score': None, 'decision': 'deferred'}
    assert request == before

def test_unhealthy_target_is_still_scored():
    request = {'cycles': [{'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [3, 73, 2, 90, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': 0.5, 'score': 5.333333, 'decision': 'alarm'}
    assert request == before

def test_missing_training_is_excluded():
    request = {'cycles': [{'id': 'missing', 'run': 'missing', 'start': 0, 'end': 1, 'features': [None, 100], 'profile': [100, 100, 0, 130, 0]}, {'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': 0.5, 'score': 5.333333, 'decision': 'alarm'}
    assert request == before

def test_empty_history():
    request = {'cycles': [{'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': [], 'center': None, 'scale': None, 'correlation': None, 'score': None, 'decision': 'insufficient_training'}
    assert request == before

def test_one_training_cycle():
    request = {'cycles': [{'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a'], 'center': None, 'scale': None, 'correlation': None, 'score': None, 'decision': 'insufficient_training'}
    assert request == before

def test_order_independent_selection():
    request = {'cycles': [{'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': 0.5, 'score': 5.333333, 'decision': 'alarm'}
    assert request == before

def test_threshold_before_rounding():
    request = {'cycles': [{'id': 'a', 'run': 'a', 'start': 0, 'end': 1, 'features': [0, 0], 'profile': [100, 100, 0, 130, 0]}, {'id': 'b', 'run': 'b', 'start': 2, 'end': 3, 'features': [2, 2], 'profile': [100, 100, 0, 130, 0]}, {'id': 't', 'run': 'target-run', 'start': 10, 'end': 11, 'features': [3, 1], 'profile': [100, 100, 0, 130, 0]}], 'target': 't', 'embargo': 1, 'min_train': 2, 'shrinkage': 0.5, 'threshold': 5.3333332}
    before = copy.deepcopy(request)
    assert run(request) == {'training': ['a', 'b'], 'center': [1.0, 1.0], 'scale': [1.0, 1.0], 'correlation': 0.5, 'score': 5.333333, 'decision': 'alarm'}
    assert request == before

