import copy
import pytest
from fabops.domain import run


def test_old_epoch_is_stale():
    request = {'sources': ['a'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 1, 'through': 1, 'watermark': 3, 'events': [{'sequence': 1, 'time': 3, 'value': 3}], 'crash': False}, {'op': 'page', 'source': 'a', 'epoch': 0, 'through': 2, 'watermark': 4, 'events': [{'sequence': 2, 'time': 4, 'value': 20}], 'crash': False}, {'op': 'snapshot'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'stale', 'published'], 'snapshot': {'cut': 3, 'epochs': {'a': 1}, 'values': {'a': 3}}, 'frontiers': {'a': [1, 2, 3]}}
    assert request == before

def test_new_epoch_blocks_snapshot():
    request = {'sources': ['a'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'through': 1, 'watermark': 8, 'events': [{'sequence': 1, 'time': 8, 'value': 8}], 'crash': False}, {'op': 'snapshot'}, {'op': 'page', 'source': 'a', 'epoch': 1, 'through': 2, 'watermark': 2, 'events': [{'sequence': 2, 'time': 2, 'value': 20}], 'crash': False}, {'op': 'restart'}, {'op': 'snapshot'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'published', 'accepted', 'restarted', 'blocked'], 'snapshot': {'cut': 8, 'epochs': {'a': 0}, 'values': {'a': 8}}, 'frontiers': {'a': [1, 1, -1]}}
    assert request == before

def test_reordered_page_drains():
    request = {'sources': ['a'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'through': 2, 'watermark': 4, 'events': [{'sequence': 2, 'time': 4, 'value': 20}], 'crash': False}, {'op': 'page', 'source': 'a', 'epoch': 0, 'through': 1, 'watermark': 2, 'events': [{'sequence': 1, 'time': 2, 'value': 10}], 'crash': False}, {'op': 'snapshot'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'accepted', 'published'], 'snapshot': {'cut': 4, 'epochs': {'a': 0}, 'values': {'a': 20}}, 'frontiers': {'a': [0, 3, 4]}}
    assert request == before

def test_identical_retry():
    request = {'sources': ['a'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'through': 1, 'watermark': 2, 'events': [{'sequence': 1, 'time': 2, 'value': 10}], 'crash': False}, {'op': 'page', 'source': 'a', 'epoch': 0, 'through': 1, 'watermark': 2, 'events': [{'sequence': 1, 'time': 2, 'value': 10}], 'crash': False}, {'op': 'restart'}, {'op': 'snapshot'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'accepted', 'restarted', 'published'], 'snapshot': {'cut': 2, 'epochs': {'a': 0}, 'values': {'a': 10}}, 'frontiers': {'a': [0, 2, 2]}}
    assert request == before

def test_conflict_rolls_back_whole_page():
    request = {'sources': ['a'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'through': 1, 'watermark': 2, 'events': [{'sequence': 1, 'time': 2, 'value': 10}], 'crash': False}, {'op': 'page', 'source': 'a', 'epoch': 0, 'through': 2, 'watermark': 4, 'events': [{'sequence': 2, 'time': 4, 'value': 20}, {'sequence': 1, 'time': 2, 'value': 99}], 'crash': False}, {'op': 'restart'}, {'op': 'snapshot'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'conflict', 'restarted', 'published'], 'snapshot': {'cut': 2, 'epochs': {'a': 0}, 'values': {'a': 10}}, 'frontiers': {'a': [0, 2, 2]}}
    assert request == before

def test_empty_certified_source():
    request = {'sources': ['a'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'through': 0, 'watermark': 4, 'events': [], 'crash': False}, {'op': 'snapshot'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'published'], 'snapshot': {'cut': 4, 'epochs': {'a': 0}, 'values': {'a': None}}, 'frontiers': {'a': [0, 1, 4]}}
    assert request == before

def test_barrier_ahead_of_data():
    request = {'sources': ['a'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'through': 3, 'watermark': 9, 'events': [], 'crash': False}, {'op': 'page', 'source': 'a', 'epoch': 0, 'through': 1, 'watermark': 2, 'events': [{'sequence': 1, 'time': 2, 'value': 10}], 'crash': False}, {'op': 'page', 'source': 'a', 'epoch': 0, 'through': 2, 'watermark': 4, 'events': [{'sequence': 2, 'time': 4, 'value': 20}], 'crash': False}, {'op': 'snapshot'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'accepted', 'accepted', 'published'], 'snapshot': {'cut': 4, 'epochs': {'a': 0}, 'values': {'a': 20}}, 'frontiers': {'a': [0, 3, 4]}}
    assert request == before

def test_snapshot_crash_is_not_publication():
    request = {'sources': ['a'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'through': 1, 'watermark': 2, 'events': [{'sequence': 1, 'time': 2, 'value': 10}], 'crash': False}, {'op': 'snapshot', 'crash': True}, {'op': 'restart'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'crashed', 'restarted'], 'snapshot': None, 'frontiers': {'a': [0, 2, 2]}}
    assert request == before

def test_failed_snapshot_keeps_prior_cut():
    request = {'sources': ['a'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'through': 1, 'watermark': 2, 'events': [{'sequence': 1, 'time': 2, 'value': 10}], 'crash': False}, {'op': 'snapshot'}, {'op': 'page', 'source': 'a', 'epoch': 0, 'through': 2, 'watermark': 4, 'events': [{'sequence': 2, 'time': 4, 'value': 20}], 'crash': False}, {'op': 'snapshot', 'crash': True}, {'op': 'restart'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'published', 'accepted', 'crashed', 'restarted'], 'snapshot': {'cut': 2, 'epochs': {'a': 0}, 'values': {'a': 10}}, 'frontiers': {'a': [0, 3, 4]}}
    assert request == before

def test_page_crash_rolls_back_cursor():
    request = {'sources': ['a'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'through': 1, 'watermark': 2, 'events': [{'sequence': 1, 'time': 2, 'value': 10}], 'crash': False}, {'op': 'page', 'source': 'a', 'epoch': 0, 'through': 2, 'watermark': 4, 'events': [{'sequence': 2, 'time': 4, 'value': 20}], 'crash': True}, {'op': 'restart'}, {'op': 'snapshot'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'crashed', 'restarted', 'published'], 'snapshot': {'cut': 2, 'epochs': {'a': 0}, 'values': {'a': 10}}, 'frontiers': {'a': [0, 2, 2]}}
    assert request == before

def test_source_epochs_are_independent():
    request = {'sources': ['a', 'b'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 2, 'through': 1, 'watermark': 3, 'events': [{'sequence': 1, 'time': 1, 'value': 7}], 'crash': False}, {'op': 'page', 'source': 'b', 'epoch': 1, 'through': 1, 'watermark': 2, 'events': [{'sequence': 1, 'time': 2, 'value': 8}], 'crash': False}, {'op': 'snapshot'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'accepted', 'published'], 'snapshot': {'cut': 2, 'epochs': {'a': 2, 'b': 1}, 'values': {'a': 7, 'b': 8}}, 'frontiers': {'a': [2, 2, 3], 'b': [1, 2, 2]}}
    assert request == before

def test_exclude_future_value():
    request = {'sources': ['a', 'b'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'through': 2, 'watermark': 5, 'events': [{'sequence': 1, 'time': 1, 'value': 1}, {'sequence': 2, 'time': 5, 'value': 5}], 'crash': False}, {'op': 'page', 'source': 'b', 'epoch': 0, 'through': 1, 'watermark': 3, 'events': [{'sequence': 1, 'time': 3, 'value': 3}], 'crash': False}, {'op': 'snapshot'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'accepted', 'published'], 'snapshot': {'cut': 3, 'epochs': {'a': 0, 'b': 0}, 'values': {'a': 1, 'b': 3}}, 'frontiers': {'a': [0, 3, 5], 'b': [0, 2, 3]}}
    assert request == before

def test_unseen_source_blocks():
    request = {'sources': ['a', 'b'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'through': 1, 'watermark': 2, 'events': [{'sequence': 1, 'time': 2, 'value': 10}], 'crash': False}, {'op': 'snapshot'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'blocked'], 'snapshot': None, 'frontiers': {'a': [0, 2, 2], 'b': [0, 1, -1]}}
    assert request == before

def test_timestamp_tie_uses_sequence():
    request = {'sources': ['a'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'through': 2, 'watermark': 2, 'events': [{'sequence': 2, 'time': 2, 'value': 0}, {'sequence': 1, 'time': 2, 'value': 9}], 'crash': False}, {'op': 'snapshot'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'published'], 'snapshot': {'cut': 2, 'epochs': {'a': 0}, 'values': {'a': 0}}, 'frontiers': {'a': [0, 3, 2]}}
    assert request == before

def test_pending_barrier_and_buffer_survive_two_restarts():
    request = {'sources': ['a'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'through': 3, 'watermark': 6, 'events': [{'sequence': 3, 'time': 6, 'value': 30}], 'crash': False}, {'op': 'restart'}, {'op': 'page', 'source': 'a', 'epoch': 0, 'through': 1, 'watermark': 2, 'events': [{'sequence': 1, 'time': 2, 'value': 10}], 'crash': False}, {'op': 'restart'}, {'op': 'page', 'source': 'a', 'epoch': 0, 'through': 2, 'watermark': 4, 'events': [{'sequence': 2, 'time': 4, 'value': 20}], 'crash': False}, {'op': 'snapshot'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'restarted', 'accepted', 'restarted', 'accepted', 'published'], 'snapshot': {'cut': 6, 'epochs': {'a': 0}, 'values': {'a': 30}}, 'frontiers': {'a': [0, 4, 6]}}
    assert request == before

def test_earlier_event_dependency_poison():
    request = {'sources': ['a', 'b'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'events': [{'sequence': 1, 'time': 1, 'value': 1, 'depends': [['b', 0, 1]]}, {'sequence': 2, 'time': 2, 'value': 99, 'depends': []}], 'through': 2, 'watermark': 10}, {'op': 'page', 'source': 'b', 'epoch': 0, 'events': [], 'through': 0, 'watermark': 10}, {'op': 'snapshot'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'accepted', 'published'], 'snapshot': {'cut': 10, 'epochs': {'a': 0, 'b': 0}, 'values': {'a': None, 'b': None}}, 'frontiers': {'a': [0, 3, 10], 'b': [0, 1, 10]}}
    assert request == before

def test_causal_cascade_after_checkpoint_restart():
    request = {'sources': ['a', 'b', 'c'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'events': [{'sequence': 1, 'time': 1, 'value': 1, 'depends': [['b', 0, 1]]}], 'through': 1, 'watermark': 10}, {'op': 'page', 'source': 'b', 'epoch': 0, 'events': [{'sequence': 1, 'time': 1, 'value': 2, 'depends': [['c', 0, 1]]}], 'through': 1, 'watermark': 10}, {'op': 'page', 'source': 'c', 'epoch': 0, 'events': [], 'through': 0, 'watermark': 10}, {'op': 'restart'}, {'op': 'snapshot'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'accepted', 'accepted', 'restarted', 'published'], 'snapshot': {'cut': 10, 'epochs': {'a': 0, 'b': 0, 'c': 0}, 'values': {'a': None, 'b': None, 'c': None}}, 'frontiers': {'a': [0, 2, 10], 'b': [0, 2, 10], 'c': [0, 1, 10]}}
    assert request == before

def test_retain_safe_prefix():
    request = {'sources': ['a', 'b'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'events': [{'sequence': 1, 'time': 1, 'value': 1, 'depends': []}, {'sequence': 2, 'time': 2, 'value': 2, 'depends': [['b', 0, 1]]}, {'sequence': 3, 'time': 3, 'value': 3, 'depends': []}], 'through': 3, 'watermark': 10}, {'op': 'page', 'source': 'b', 'epoch': 0, 'events': [], 'through': 0, 'watermark': 10}, {'op': 'snapshot'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'accepted', 'published'], 'snapshot': {'cut': 10, 'epochs': {'a': 0, 'b': 0}, 'values': {'a': 1, 'b': None}}, 'frontiers': {'a': [0, 4, 10], 'b': [0, 1, 10]}}
    assert request == before

def test_mutual_dependencies_are_closed():
    request = {'sources': ['a', 'b'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'events': [{'sequence': 1, 'time': 1, 'value': 10, 'depends': [['b', 0, 1]]}], 'through': 1, 'watermark': 10}, {'op': 'page', 'source': 'b', 'epoch': 0, 'events': [{'sequence': 1, 'time': 1, 'value': 20, 'depends': [['a', 0, 1]]}], 'through': 1, 'watermark': 10}, {'op': 'snapshot'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'accepted', 'published'], 'snapshot': {'cut': 10, 'epochs': {'a': 0, 'b': 0}, 'values': {'a': 10, 'b': 20}}, 'frontiers': {'a': [0, 2, 10], 'b': [0, 2, 10]}}
    assert request == before

def test_wrong_dependency_epoch():
    request = {'sources': ['a', 'b'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'events': [{'sequence': 1, 'time': 1, 'value': 10, 'depends': [['b', 0, 1]]}], 'through': 1, 'watermark': 10}, {'op': 'page', 'source': 'b', 'epoch': 1, 'events': [{'sequence': 1, 'time': 1, 'value': 20, 'depends': []}], 'through': 1, 'watermark': 10}, {'op': 'snapshot'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'accepted', 'published'], 'snapshot': {'cut': 10, 'epochs': {'a': 0, 'b': 1}, 'values': {'a': None, 'b': 20}}, 'frontiers': {'a': [0, 2, 10], 'b': [1, 2, 10]}}
    assert request == before

def test_required_floor_blocks():
    request = {'sources': ['a', 'b'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'events': [{'sequence': 1, 'time': 1, 'value': 10, 'depends': [['b', 0, 1]]}], 'through': 1, 'watermark': 10}, {'op': 'page', 'source': 'b', 'epoch': 0, 'events': [], 'through': 0, 'watermark': 10}, {'op': 'snapshot', 'required': {'a': [0, 1]}}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'accepted', 'blocked'], 'snapshot': None, 'frontiers': {'a': [0, 2, 10], 'b': [0, 1, 10]}}
    assert request == before

def test_required_epoch_blocks():
    request = {'sources': ['a'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'events': [{'sequence': 1, 'time': 1, 'value': 10, 'depends': []}], 'through': 1, 'watermark': 10}, {'op': 'snapshot', 'required': {'a': [1, 1]}}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'blocked'], 'snapshot': None, 'frontiers': {'a': [0, 2, 10]}}
    assert request == before

def test_future_event_outside_cut():
    request = {'sources': ['a', 'b'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'events': [{'sequence': 1, 'time': 1, 'value': 10, 'depends': [['b', 0, 1]]}], 'through': 1, 'watermark': 10}, {'op': 'page', 'source': 'b', 'epoch': 0, 'events': [{'sequence': 1, 'time': 12, 'value': 20, 'depends': []}], 'through': 1, 'watermark': 20}, {'op': 'snapshot'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'accepted', 'published'], 'snapshot': {'cut': 10, 'epochs': {'a': 0, 'b': 0}, 'values': {'a': None, 'b': None}}, 'frontiers': {'a': [0, 2, 10], 'b': [0, 2, 20]}}
    assert request == before

def test_gapped_dependency_prefix():
    request = {'sources': ['a', 'b'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'events': [{'sequence': 1, 'time': 1, 'value': 10, 'depends': [['b', 0, 1]]}], 'through': 1, 'watermark': 10}, {'op': 'page', 'source': 'b', 'epoch': 0, 'events': [{'sequence': 2, 'time': 12, 'value': 20, 'depends': []}], 'through': 0, 'watermark': 10}, {'op': 'snapshot'}, {'op': 'restart'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'accepted', 'published', 'restarted'], 'snapshot': {'cut': 10, 'epochs': {'a': 0, 'b': 0}, 'values': {'a': None, 'b': None}}, 'frontiers': {'a': [0, 2, 10], 'b': [0, 1, 10]}}
    assert request == before

def test_crashed_causal_publication():
    request = {'sources': ['a', 'b'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'events': [{'sequence': 1, 'time': 1, 'value': 10, 'depends': [['b', 0, 1]]}], 'through': 1, 'watermark': 10}, {'op': 'page', 'source': 'b', 'epoch': 0, 'events': [{'sequence': 1, 'time': 1, 'value': 20, 'depends': []}], 'through': 1, 'watermark': 10}, {'op': 'snapshot', 'crash': True}, {'op': 'restart'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'accepted', 'crashed', 'restarted'], 'snapshot': None, 'frontiers': {'a': [0, 2, 10], 'b': [0, 2, 10]}}
    assert request == before

def test_zero_floor_does_not_require_event():
    request = {'sources': ['a', 'b'], 'commands': [{'op': 'page', 'source': 'a', 'epoch': 0, 'events': [{'sequence': 1, 'time': 1, 'value': 10, 'depends': [['b', 0, 1]]}], 'through': 1, 'watermark': 10}, {'op': 'page', 'source': 'b', 'epoch': 0, 'events': [], 'through': 0, 'watermark': 10}, {'op': 'snapshot', 'required': {'a': [0, 0]}}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['accepted', 'accepted', 'published'], 'snapshot': {'cut': 10, 'epochs': {'a': 0, 'b': 0}, 'values': {'a': None, 'b': None}}, 'frontiers': {'a': [0, 2, 10], 'b': [0, 1, 10]}}
    assert request == before

