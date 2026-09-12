import copy
import pytest
from fabops.domain import run


def test_maintenance_split():
    request = {'lots': [{'id': 'a', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0}, 'durations': {'x': 2}, 'release': 0, 'deadline': 4}], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'horizon': 4, 'observed': {'dispatch': 1, 'calendar': 1}, 'current': {'dispatch': 1, 'calendar': 1}, 'maintenance': {'x': [[1, 2]]}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [['a', 'x', 2, 4]], 'status': 'committed', 'reservations': [['a', 'x', 2, 4]]}
    assert request == before

def test_precedence_and_cooldown_across_tools():
    request = {'lots': [{'id': 'a', 'priority': 1, 'reticle': 'r', 'costs': {'y': 0}, 'durations': {'y': 1}, 'release': 0, 'deadline': 4, 'after': ['z']}, {'id': 'z', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0}, 'durations': {'x': 1}, 'release': 0, 'deadline': 4, 'cooldown': 2}], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'horizon': 4, 'observed': {'dispatch': 1, 'calendar': 1}, 'current': {'dispatch': 1, 'calendar': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [['a', 'y', 3, 4], ['z', 'x', 0, 1]], 'status': 'committed', 'reservations': [['a', 'y', 3, 4], ['z', 'x', 0, 1]]}
    assert request == before

def test_maintenance_union():
    request = {'lots': [{'id': 'a', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0}, 'durations': {'x': 2}, 'release': 0, 'deadline': 4}], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'horizon': 4, 'observed': {'dispatch': 1, 'calendar': 1}, 'current': {'dispatch': 1, 'calendar': 1}, 'maintenance': {'x': [[0, 2], [1, 3]]}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [], 'status': 'committed', 'reservations': []}
    assert request == before

def test_release():
    request = {'lots': [{'id': 'a', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0}, 'durations': {'x': 1}, 'release': 2, 'deadline': 4}], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'horizon': 4, 'observed': {'dispatch': 1, 'calendar': 1}, 'current': {'dispatch': 1, 'calendar': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [['a', 'x', 2, 3]], 'status': 'committed', 'reservations': [['a', 'x', 2, 3]]}
    assert request == before

def test_deadline():
    request = {'lots': [{'id': 'a', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0}, 'durations': {'x': 2}, 'release': 0, 'deadline': 1}], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'horizon': 4, 'observed': {'dispatch': 1, 'calendar': 1}, 'current': {'dispatch': 1, 'calendar': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [], 'status': 'committed', 'reservations': []}
    assert request == before

def test_weighted_stock():
    request = {'lots': [{'id': 'a', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0}, 'durations': {'x': 1}, 'release': 0, 'deadline': 4, 'units': 2}], 'tools': ['x', 'y'], 'stock': {'r': 1}, 'horizon': 4, 'observed': {'dispatch': 1, 'calendar': 1}, 'current': {'dispatch': 1, 'calendar': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [], 'status': 'committed', 'reservations': []}
    assert request == before

def test_parallel_capacity():
    request = {'lots': [{'id': 'a', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0}, 'durations': {'x': 1}, 'release': 0, 'deadline': 4}, {'id': 'b', 'priority': 1, 'reticle': 'r', 'costs': {'y': 0}, 'durations': {'y': 1}, 'release': 0, 'deadline': 4}], 'tools': ['x', 'y'], 'stock': {'r': 2}, 'horizon': 4, 'observed': {'dispatch': 1, 'calendar': 1}, 'current': {'dispatch': 1, 'calendar': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [['a', 'x', 0, 1], ['b', 'y', 0, 1]], 'status': 'committed', 'reservations': [['a', 'x', 0, 1], ['b', 'y', 0, 1]]}
    assert request == before

def test_reticle_blocks_parallel():
    request = {'lots': [{'id': 'a', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0}, 'durations': {'x': 1}, 'release': 0, 'deadline': 4}, {'id': 'b', 'priority': 1, 'reticle': 'r', 'costs': {'y': 0}, 'durations': {'y': 1}, 'release': 0, 'deadline': 4}], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'horizon': 4, 'observed': {'dispatch': 1, 'calendar': 1}, 'current': {'dispatch': 1, 'calendar': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [['a', 'x', 0, 1], ['b', 'y', 1, 2]], 'status': 'committed', 'reservations': [['a', 'x', 0, 1], ['b', 'y', 1, 2]]}
    assert request == before

def test_cost_before_finish():
    request = {'lots': [{'id': 'a', 'priority': 1, 'reticle': 'r', 'costs': {'x': 4, 'y': 0}, 'durations': {'x': 1, 'y': 1}, 'release': 0, 'deadline': 4}], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'horizon': 4, 'observed': {'dispatch': 1, 'calendar': 1}, 'current': {'dispatch': 1, 'calendar': 1}, 'maintenance': {'y': [[0, 2]]}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [['a', 'y', 2, 3]], 'status': 'committed', 'reservations': [['a', 'y', 2, 3]]}
    assert request == before

def test_throughput_before_priority():
    request = {'lots': [{'id': 'a', 'priority': 99, 'reticle': 'r', 'costs': {'x': 0}, 'durations': {'x': 4}, 'release': 0, 'deadline': 4}, {'id': 'b', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0}, 'durations': {'x': 2}, 'release': 0, 'deadline': 4}, {'id': 'c', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0}, 'durations': {'x': 2}, 'release': 0, 'deadline': 4}], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'horizon': 4, 'observed': {'dispatch': 1, 'calendar': 1}, 'current': {'dispatch': 1, 'calendar': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [['b', 'x', 0, 2], ['c', 'x', 2, 4]], 'status': 'committed', 'reservations': [['b', 'x', 0, 2], ['c', 'x', 2, 4]]}
    assert request == before

def test_unavailable_predecessor():
    request = {'lots': [{'id': 'a', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0}, 'durations': {'x': 1}, 'release': 0, 'deadline': 4, 'after': ['z']}, {'id': 'z', 'priority': 1, 'reticle': 'missing', 'costs': {'x': 0}, 'durations': {'x': 1}, 'release': 0, 'deadline': 4}], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'horizon': 4, 'observed': {'dispatch': 1, 'calendar': 1}, 'current': {'dispatch': 1, 'calendar': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [], 'status': 'committed', 'reservations': []}
    assert request == before

def test_stale_calendar():
    request = {'lots': [{'id': 'a', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0}, 'durations': {'x': 1}, 'release': 0, 'deadline': 4}], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'horizon': 4, 'observed': {'dispatch': 1, 'calendar': 1}, 'current': {'dispatch': 1, 'calendar': 2}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [['a', 'x', 0, 1]], 'status': 'stale', 'reservations': []}
    assert request == before

def test_extra_revision_key():
    request = {'lots': [{'id': 'a', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0}, 'durations': {'x': 1}, 'release': 0, 'deadline': 4}], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'horizon': 4, 'observed': {'dispatch': 1, 'calendar': 1}, 'current': {'dispatch': 1, 'calendar': 1, 'stock': 0}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [['a', 'x', 0, 1]], 'status': 'stale', 'reservations': []}
    assert request == before

def test_crash_after_insert():
    request = {'lots': [{'id': 'a', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0}, 'durations': {'x': 1}, 'release': 0, 'deadline': 4}, {'id': 'b', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0}, 'durations': {'x': 1}, 'release': 0, 'deadline': 4}], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'horizon': 4, 'observed': {'dispatch': 1, 'calendar': 1}, 'current': {'dispatch': 1, 'calendar': 1}, 'crash': True}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [['a', 'x', 0, 1], ['b', 'x', 1, 2]], 'status': 'crashed', 'reservations': []}
    assert request == before

def test_stale_before_crash():
    request = {'lots': [], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'horizon': 4, 'observed': {'dispatch': 1, 'calendar': 1}, 'current': {}, 'crash': True}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [], 'status': 'stale', 'reservations': []}
    assert request == before

def test_short_deadline_forces_idle():
    request = {'lots': [{'id': 'a', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0}, 'durations': {'x': 2}, 'release': 0, 'deadline': 4}, {'id': 'b', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0}, 'durations': {'x': 1}, 'release': 0, 'deadline': 1}], 'tools': ['x', 'y'], 'stock': {'r': 1, 's': 1}, 'horizon': 4, 'observed': {'dispatch': 1, 'calendar': 1}, 'current': {'dispatch': 1, 'calendar': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [['a', 'x', 1, 3], ['b', 'x', 0, 1]], 'status': 'committed', 'reservations': [['a', 'x', 1, 3], ['b', 'x', 0, 1]]}
    assert request == before

def test_full_six_lot_search():
    request = {'lots': [{'id': 'a', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0, 'y': 0, 'z': 0}, 'durations': {'x': 1, 'y': 1, 'z': 1}, 'release': 0, 'deadline': 8}, {'id': 'b', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0, 'y': 0, 'z': 0}, 'durations': {'x': 1, 'y': 1, 'z': 1}, 'release': 0, 'deadline': 8}, {'id': 'c', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0, 'y': 0, 'z': 0}, 'durations': {'x': 1, 'y': 1, 'z': 1}, 'release': 0, 'deadline': 8}, {'id': 'd', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0, 'y': 0, 'z': 0}, 'durations': {'x': 1, 'y': 1, 'z': 1}, 'release': 0, 'deadline': 8}, {'id': 'e', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0, 'y': 0, 'z': 0}, 'durations': {'x': 1, 'y': 1, 'z': 1}, 'release': 0, 'deadline': 8}, {'id': 'f', 'priority': 1, 'reticle': 'r', 'costs': {'x': 0, 'y': 0, 'z': 0}, 'durations': {'x': 1, 'y': 1, 'z': 1}, 'release': 0, 'deadline': 8}], 'tools': ['x', 'y', 'z'], 'stock': {'r': 6}, 'horizon': 8, 'observed': {'dispatch': 1, 'calendar': 1}, 'current': {'dispatch': 1, 'calendar': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'plan': [['a', 'x', 0, 1], ['b', 'x', 1, 2], ['c', 'y', 0, 1], ['d', 'y', 1, 2], ['e', 'z', 0, 1], ['f', 'z', 1, 2]], 'status': 'committed', 'reservations': [['a', 'x', 0, 1], ['b', 'x', 1, 2], ['c', 'y', 0, 1], ['d', 'y', 1, 2], ['e', 'z', 0, 1], ['f', 'z', 1, 2]]}
    assert request == before

