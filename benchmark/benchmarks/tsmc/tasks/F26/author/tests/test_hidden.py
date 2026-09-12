import copy
import pytest
from fabops.domain import run


def test_empty_log():
    request = {'events': []}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 0, 'alternatives': 1, 'certain_pairs': [], 'certain_unmatched': [], 'duration_bounds': [0, 0]}
    assert request == before

def test_orphan_completion():
    request = {'events': [{'id': 'c', 'kind': 'complete', 'time': 8, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 0, 'alternatives': 1, 'certain_pairs': [], 'certain_unmatched': ['c'], 'duration_bounds': [0, 0]}
    assert request == before

def test_negative_duration_forbidden():
    request = {'events': [{'id': 's', 'kind': 'start', 'time': 5, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}, {'id': 'c', 'kind': 'complete', 'time': 4, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 0, 'alternatives': 1, 'certain_pairs': [], 'certain_unmatched': ['c', 's'], 'duration_bounds': [0, 0]}
    assert request == before

def test_zero_duration_allowed():
    request = {'events': [{'id': 's', 'kind': 'start', 'time': 5, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}, {'id': 'c', 'kind': 'complete', 'time': 5, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 1, 'alternatives': 1, 'certain_pairs': [['s', 'c']], 'certain_unmatched': [], 'duration_bounds': [0, 0]}
    assert request == before

def test_case_boundary():
    request = {'events': [{'id': 's', 'kind': 'start', 'time': 1, 'case': 'a', 'activity': 'etch', 'resource': 'tool'}, {'id': 'c', 'kind': 'complete', 'time': 3, 'case': 'b', 'activity': 'etch', 'resource': 'tool'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 0, 'alternatives': 1, 'certain_pairs': [], 'certain_unmatched': ['c', 's'], 'duration_bounds': [0, 0]}
    assert request == before

def test_resource_boundary():
    request = {'events': [{'id': 's', 'kind': 'start', 'time': 1, 'case': 'lot', 'activity': 'etch', 'resource': 'a'}, {'id': 'c', 'kind': 'complete', 'time': 3, 'case': 'lot', 'activity': 'etch', 'resource': 'b'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 0, 'alternatives': 1, 'certain_pairs': [], 'certain_unmatched': ['c', 's'], 'duration_bounds': [0, 0]}
    assert request == before

def test_activity_boundary():
    request = {'events': [{'id': 's', 'kind': 'start', 'time': 1, 'case': 'lot', 'activity': 'clean', 'resource': 'tool'}, {'id': 'c', 'kind': 'complete', 'time': 3, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 0, 'alternatives': 1, 'certain_pairs': [], 'certain_unmatched': ['c', 's'], 'duration_bounds': [0, 0]}
    assert request == before

def test_unknown_correlation_requires_global_choice():
    request = {'events': [{'id': 's1', 'kind': 'start', 'time': 0, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}, {'id': 's2', 'kind': 'start', 'time': 1, 'case': 'lot', 'activity': 'etch', 'resource': 'tool', 'run': 'a'}, {'id': 'c1', 'kind': 'complete', 'time': 3, 'case': 'lot', 'activity': 'etch', 'resource': 'tool', 'run': 'a'}, {'id': 'c2', 'kind': 'complete', 'time': 4, 'case': 'lot', 'activity': 'etch', 'resource': 'tool', 'run': 'b'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 2, 'alternatives': 1, 'certain_pairs': [['s1', 'c2'], ['s2', 'c1']], 'certain_unmatched': [], 'duration_bounds': [6, 6]}
    assert request == before

def test_possible_unmatched_is_not_certain():
    request = {'events': [{'id': 's1', 'kind': 'start', 'time': 1, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}, {'id': 's2', 'kind': 'start', 'time': 4, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}, {'id': 'c', 'kind': 'complete', 'time': 7, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 1, 'alternatives': 2, 'certain_pairs': [], 'certain_unmatched': [], 'duration_bounds': [3, 6]}
    assert request == before

def test_surplus_completions_duration_range():
    request = {'events': [{'id': 's', 'kind': 'start', 'time': 1, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}, {'id': 'c1', 'kind': 'complete', 'time': 4, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}, {'id': 'c2', 'kind': 'complete', 'time': 8, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 1, 'alternatives': 2, 'certain_pairs': [], 'certain_unmatched': [], 'duration_bounds': [3, 7]}
    assert request == before

def test_mixed_forced_ambiguous_and_orphan():
    request = {'events': [{'id': 's1', 'kind': 'start', 'time': 0, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}, {'id': 's2', 'kind': 'start', 'time': 1, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}, {'id': 'c1', 'kind': 'complete', 'time': 2, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}, {'id': 'c2', 'kind': 'complete', 'time': 3, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}, {'id': 's3', 'kind': 'start', 'time': 4, 'case': 'lot', 'activity': 'etch', 'resource': 'other'}, {'id': 'c3', 'kind': 'complete', 'time': 6, 'case': 'lot', 'activity': 'etch', 'resource': 'other'}, {'id': 'orphan', 'kind': 'complete', 'time': 9, 'case': 'other', 'activity': 'etch', 'resource': 'tool'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 3, 'alternatives': 2, 'certain_pairs': [['s3', 'c3']], 'certain_unmatched': ['orphan'], 'duration_bounds': [6, 6]}
    assert request == before

def test_simultaneous_distinct_ids():
    request = {'events': [{'id': 's1', 'kind': 'start', 'time': 1, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}, {'id': 's2', 'kind': 'start', 'time': 1, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}, {'id': 'c1', 'kind': 'complete', 'time': 2, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}, {'id': 'c2', 'kind': 'complete', 'time': 2, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 2, 'alternatives': 2, 'certain_pairs': [], 'certain_unmatched': [], 'duration_bounds': [2, 2]}
    assert request == before

def test_conflicting_retry_rejected():
    request = {'events': [{'id': 's', 'kind': 'start', 'time': 1, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}, {'id': 's', 'kind': 'start', 'time': 2, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}]}
    before = copy.deepcopy(request)
    with pytest.raises(ValueError):
        run(request)
    assert request == before

def test_out_of_order_transport():
    request = {'events': [{'id': 'c2', 'kind': 'complete', 'time': 8, 'case': 'lot', 'activity': 'etch', 'resource': 'tool', 'run': 'b'}, {'id': 's1', 'kind': 'start', 'time': 1, 'case': 'lot', 'activity': 'etch', 'resource': 'tool', 'run': 'a'}, {'id': 'c1', 'kind': 'complete', 'time': 4, 'case': 'lot', 'activity': 'etch', 'resource': 'tool', 'run': 'a'}, {'id': 's2', 'kind': 'start', 'time': 2, 'case': 'lot', 'activity': 'etch', 'resource': 'tool', 'run': 'b'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 2, 'alternatives': 1, 'certain_pairs': [['s1', 'c1'], ['s2', 'c2']], 'certain_unmatched': [], 'duration_bounds': [9, 9]}
    assert request == before

def test_explicit_null_correlation():
    request = {'events': [{'id': 's', 'kind': 'start', 'time': 1, 'case': 'lot', 'activity': 'etch', 'resource': 'tool', 'run': None}, {'id': 'c', 'kind': 'complete', 'time': 4, 'case': 'lot', 'activity': 'etch', 'resource': 'tool', 'run': 'a'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 1, 'alternatives': 1, 'certain_pairs': [['s', 'c']], 'certain_unmatched': [], 'duration_bounds': [3, 3]}
    assert request == before

def test_retry_does_not_multiply_ambiguous_interpretations():
    request = {'events': [{'id': 's1', 'kind': 'start', 'time': 1, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}, {'id': 's2', 'kind': 'start', 'time': 4, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}, {'id': 's1', 'kind': 'start', 'time': 1, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}, {'id': 'c', 'kind': 'complete', 'time': 7, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 1, 'alternatives': 2, 'certain_pairs': [], 'certain_unmatched': [], 'duration_bounds': [3, 6]}
    assert request == before

def test_weighted_capacity():
    request = {'events': [{'id': 'as', 'kind': 'start', 'time': 0, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'a', 'units': 2}, {'id': 'ae', 'kind': 'complete', 'time': 3, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'a'}, {'id': 'bs', 'kind': 'start', 'time': 1, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'b', 'units': 1}, {'id': 'be', 'kind': 'complete', 'time': 2, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'b'}], 'capacities': {'m': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 1, 'alternatives': 1, 'certain_pairs': [['bs', 'be']], 'certain_unmatched': ['ae', 'as'], 'duration_bounds': [1, 1]}
    assert request == before

def test_coupling_at_weighted_capacity():
    request = {'events': [{'id': 'as', 'kind': 'start', 'time': 0, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'a', 'units': 2}, {'id': 'ae', 'kind': 'complete', 'time': 3, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'a'}, {'id': 'bs', 'kind': 'start', 'time': 1, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'b', 'units': 1}, {'id': 'be', 'kind': 'complete', 'time': 2, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'b'}], 'capacities': {'m': 3}, 'coupled': [['as', 'bs']]}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 2, 'alternatives': 1, 'certain_pairs': [['as', 'ae'], ['bs', 'be']], 'certain_unmatched': [], 'duration_bounds': [4, 4]}
    assert request == before

def test_touching_capacity():
    request = {'events': [{'id': 'as', 'kind': 'start', 'time': 0, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'a', 'units': 1}, {'id': 'ae', 'kind': 'complete', 'time': 1, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'a'}, {'id': 'bs', 'kind': 'start', 'time': 1, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'b', 'units': 1}, {'id': 'be', 'kind': 'complete', 'time': 2, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'b'}], 'capacities': {'m': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 2, 'alternatives': 1, 'certain_pairs': [['as', 'ae'], ['bs', 'be']], 'certain_unmatched': [], 'duration_bounds': [2, 2]}
    assert request == before

def test_zero_duration_capacity_zero():
    request = {'events': [{'id': 'as', 'kind': 'start', 'time': 1, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'a', 'units': 1}, {'id': 'ae', 'kind': 'complete', 'time': 1, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'a'}], 'capacities': {'m': 0}}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 1, 'alternatives': 1, 'certain_pairs': [['as', 'ae']], 'certain_unmatched': [], 'duration_bounds': [0, 0]}
    assert request == before

def test_cross_resource_route():
    request = {'events': [{'id': 'as', 'kind': 'start', 'time': 0, 'case': 'c', 'activity': 'etch', 'resource': 'm', 'run': 'a', 'units': 1}, {'id': 'ae', 'kind': 'complete', 'time': 3, 'case': 'c', 'activity': 'etch', 'resource': 'm', 'run': 'a'}, {'id': 'bs', 'kind': 'start', 'time': 2, 'case': 'c', 'activity': 'inspect', 'resource': 'q', 'run': 'b', 'units': 1}, {'id': 'be', 'kind': 'complete', 'time': 4, 'case': 'c', 'activity': 'inspect', 'resource': 'q', 'run': 'b'}], 'route': [['etch', 'inspect']]}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 1, 'alternatives': 2, 'certain_pairs': [], 'certain_unmatched': [], 'duration_bounds': [2, 3]}
    assert request == before

def test_route_other_case():
    request = {'events': [{'id': 'as', 'kind': 'start', 'time': 0, 'case': 'c', 'activity': 'etch', 'resource': 'm', 'run': 'a', 'units': 1}, {'id': 'ae', 'kind': 'complete', 'time': 3, 'case': 'c', 'activity': 'etch', 'resource': 'm', 'run': 'a'}, {'id': 'bs', 'kind': 'start', 'time': 2, 'case': 'other', 'activity': 'inspect', 'resource': 'm', 'run': 'b', 'units': 1}, {'id': 'be', 'kind': 'complete', 'time': 4, 'case': 'other', 'activity': 'inspect', 'resource': 'm', 'run': 'b'}], 'route': [['etch', 'inspect']]}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 2, 'alternatives': 1, 'certain_pairs': [['as', 'ae'], ['bs', 'be']], 'certain_unmatched': [], 'duration_bounds': [5, 5]}
    assert request == before

def test_route_and_coupling():
    request = {'events': [{'id': 'as', 'kind': 'start', 'time': 0, 'case': 'c', 'activity': 'etch', 'resource': 'm', 'run': 'a', 'units': 1}, {'id': 'ae', 'kind': 'complete', 'time': 3, 'case': 'c', 'activity': 'etch', 'resource': 'm', 'run': 'a'}, {'id': 'bs', 'kind': 'start', 'time': 2, 'case': 'c', 'activity': 'inspect', 'resource': 'q', 'run': 'b', 'units': 1}, {'id': 'be', 'kind': 'complete', 'time': 4, 'case': 'c', 'activity': 'inspect', 'resource': 'q', 'run': 'b'}], 'route': [['etch', 'inspect']], 'coupled': [['ae', 'be']]}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 0, 'alternatives': 1, 'certain_pairs': [], 'certain_unmatched': ['ae', 'as', 'be', 'bs'], 'duration_bounds': [0, 0]}
    assert request == before

def test_duration_before_global_max():
    request = {'events': [{'id': 'as', 'kind': 'start', 'time': 0, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'a', 'units': 1}, {'id': 'ae', 'kind': 'complete', 'time': 3, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'a'}, {'id': 'bs', 'kind': 'start', 'time': 1, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'b', 'units': 1}, {'id': 'be', 'kind': 'complete', 'time': 2, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'b'}], 'duration_limits': {'work': [2, 4]}}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 1, 'alternatives': 1, 'certain_pairs': [['as', 'ae']], 'certain_unmatched': ['be', 'bs'], 'duration_bounds': [3, 3]}
    assert request == before

def test_resource_capacity_two():
    request = {'events': [{'id': 'as', 'kind': 'start', 'time': 0, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'a', 'units': 1}, {'id': 'ae', 'kind': 'complete', 'time': 3, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'a'}, {'id': 'bs', 'kind': 'start', 'time': 1, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'b', 'units': 1}, {'id': 'be', 'kind': 'complete', 'time': 2, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'b'}, {'id': 'cs', 'kind': 'start', 'time': 2, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'c', 'units': 1}, {'id': 'ce', 'kind': 'complete', 'time': 4, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'c'}], 'capacities': {'m': 2}}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 3, 'alternatives': 1, 'certain_pairs': [['as', 'ae'], ['bs', 'be'], ['cs', 'ce']], 'certain_unmatched': [], 'duration_bounds': [6, 6]}
    assert request == before

def test_coupled_unpairable_evidence():
    request = {'events': [{'id': 'as', 'kind': 'start', 'time': 0, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'a', 'units': 1}, {'id': 'ae', 'kind': 'complete', 'time': 3, 'case': 'c', 'activity': 'work', 'resource': 'm', 'run': 'a'}, {'id': 'orphan', 'kind': 'complete', 'time': -1, 'case': 'lot', 'activity': 'etch', 'resource': 'tool'}], 'coupled': [['as', 'orphan']]}
    before = copy.deepcopy(request)
    assert run(request) == {'matched': 0, 'alternatives': 1, 'certain_pairs': [], 'certain_unmatched': ['ae', 'as', 'orphan'], 'duration_bounds': [0, 0]}
    assert request == before

