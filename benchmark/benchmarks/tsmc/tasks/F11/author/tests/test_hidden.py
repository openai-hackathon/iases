import copy
import pytest
from fabops.domain import run


def test_overlapping_open_union():
    request = {'horizon': [0, 20], 'open': [[5, 15], [0, 10], [0, 10]], 'maintenance': [], 'jobs': [], 'capacity': 2, 'query': {'ready': 0, 'duration': 14, 'units': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'profile': [[0, 15, 2], [15, 20, 0]], 'available_unit_minutes': 30, 'booking': [0, 14]}
    assert request == before

def test_nested_closure_union():
    request = {'horizon': [0, 20], 'open': [[0, 20]], 'maintenance': [[2, 8], [4, 12], [5, 6]], 'jobs': [], 'capacity': 2, 'query': {'ready': 0, 'duration': 4, 'units': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'profile': [[0, 2, 2], [2, 12, 0], [12, 20, 2]], 'available_unit_minutes': 20, 'booking': [12, 16]}
    assert request == before

def test_disjoint_closures():
    request = {'horizon': [0, 20], 'open': [[0, 20]], 'maintenance': [[2, 4], [7, 10]], 'jobs': [], 'capacity': 2, 'query': {'ready': 0, 'duration': 4, 'units': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'profile': [[0, 2, 2], [2, 4, 0], [4, 7, 2], [7, 10, 0], [10, 20, 2]], 'available_unit_minutes': 30, 'booking': [10, 14]}
    assert request == before

def test_ready_inside_segment():
    request = {'horizon': [0, 20], 'open': [[0, 20]], 'maintenance': [], 'jobs': [], 'capacity': 2, 'query': {'ready': 7, 'duration': 4, 'units': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'profile': [[0, 20, 2]], 'available_unit_minutes': 40, 'booking': [7, 11]}
    assert request == before

def test_ready_in_downtime():
    request = {'horizon': [0, 20], 'open': [[0, 20]], 'maintenance': [[4, 10]], 'jobs': [], 'capacity': 2, 'query': {'ready': 6, 'duration': 4, 'units': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'profile': [[0, 4, 2], [4, 10, 0], [10, 20, 2]], 'available_unit_minutes': 28, 'booking': [10, 14]}
    assert request == before

def test_touching_reservations():
    request = {'horizon': [0, 20], 'open': [[0, 20]], 'maintenance': [], 'jobs': [{'start': 0, 'end': 6, 'units': 1}, {'start': 6, 'end': 12, 'units': 1}], 'capacity': 2, 'query': {'ready': 0, 'duration': 4, 'units': 2}}
    before = copy.deepcopy(request)
    assert run(request) == {'profile': [[0, 12, 1], [12, 20, 2]], 'available_unit_minutes': 28, 'booking': [12, 16]}
    assert request == before

def test_duplicate_jobs_are_distinct():
    request = {'horizon': [0, 20], 'open': [[0, 20]], 'maintenance': [], 'jobs': [{'start': 5, 'end': 10, 'units': 1}, {'start': 5, 'end': 10, 'units': 1}], 'capacity': 2, 'query': {'ready': 0, 'duration': 8, 'units': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'profile': [[0, 5, 2], [5, 10, 0], [10, 20, 2]], 'available_unit_minutes': 30, 'booking': [10, 18]}
    assert request == before

def test_overbook_clamped():
    request = {'horizon': [0, 20], 'open': [[0, 20]], 'maintenance': [], 'jobs': [{'start': -1, 'end': 10, 'units': 3}], 'capacity': 2, 'query': {'ready': 0, 'duration': 4, 'units': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'profile': [[0, 10, 0], [10, 20, 2]], 'available_unit_minutes': 20, 'booking': [10, 14]}
    assert request == before

def test_outside_horizon():
    request = {'horizon': [0, 20], 'open': [[-10, 5], [15, 40]], 'maintenance': [[-20, -10], [30, 40]], 'jobs': [{'start': -9, 'end': -5, 'units': 3}, {'start': 30, 'end': 40, 'units': 4}], 'capacity': 2, 'query': {'ready': 0, 'duration': 4, 'units': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'profile': [[0, 5, 2], [5, 15, 0], [15, 20, 2]], 'available_unit_minutes': 20, 'booking': [0, 4]}
    assert request == before

def test_no_operating_hours():
    request = {'horizon': [0, 20], 'open': [], 'maintenance': [], 'jobs': [], 'capacity': 2, 'query': {'ready': 0, 'duration': 4, 'units': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'profile': [[0, 20, 0]], 'available_unit_minutes': 0, 'booking': None}
    assert request == before

def test_full_closure():
    request = {'horizon': [0, 20], 'open': [[0, 20]], 'maintenance': [[-1, 21]], 'jobs': [], 'capacity': 2, 'query': {'ready': 0, 'duration': 4, 'units': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'profile': [[0, 20, 0]], 'available_unit_minutes': 0, 'booking': None}
    assert request == before

def test_insufficient_total_capacity():
    request = {'horizon': [0, 20], 'open': [[0, 20]], 'maintenance': [], 'jobs': [], 'capacity': 2, 'query': {'ready': 0, 'duration': 4, 'units': 3}}
    before = copy.deepcopy(request)
    assert run(request) == {'profile': [[0, 20, 2]], 'available_unit_minutes': 40, 'booking': None}
    assert request == before

def test_right_boundary_exact():
    request = {'horizon': [0, 20], 'open': [[0, 20]], 'maintenance': [], 'jobs': [], 'capacity': 2, 'query': {'ready': 16, 'duration': 4, 'units': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'profile': [[0, 20, 2]], 'available_unit_minutes': 40, 'booking': [16, 20]}
    assert request == before

def test_right_boundary_too_late():
    request = {'horizon': [0, 20], 'open': [[0, 20]], 'maintenance': [], 'jobs': [], 'capacity': 2, 'query': {'ready': 17, 'duration': 4, 'units': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'profile': [[0, 20, 2]], 'available_unit_minutes': 40, 'booking': None}
    assert request == before

def test_separate_short_windows():
    request = {'horizon': [0, 20], 'open': [[0, 3], [10, 13]], 'maintenance': [], 'jobs': [], 'capacity': 2, 'query': {'ready': 0, 'duration': 5, 'units': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'profile': [[0, 3, 2], [3, 10, 0], [10, 13, 2], [13, 20, 0]], 'available_unit_minutes': 12, 'booking': None}
    assert request == before

def test_negative_absolute_time():
    request = {'horizon': [-20, 0], 'open': [[-20, 0]], 'maintenance': [[-10, -5]], 'jobs': [], 'capacity': 2, 'query': {'ready': -30, 'duration': 4, 'units': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'profile': [[-20, -10, 2], [-10, -5, 0], [-5, 0, 2]], 'available_unit_minutes': 30, 'booking': [-20, -16]}
    assert request == before

def test_billion_minute_horizon():
    request = {'horizon': [0, 1000000000], 'open': [[0, 1000000000]], 'maintenance': [[500000000, 500000001]], 'jobs': [], 'capacity': 2, 'query': {'ready': 499999998, 'duration': 5, 'units': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'profile': [[0, 500000000, 2], [500000000, 500000001, 0], [500000001, 1000000000, 2]], 'available_unit_minutes': 1999999998, 'booking': [500000001, 500000006]}
    assert request == before

def test_maximal_segments_despite_boundaries():
    request = {'horizon': [0, 20], 'open': [], 'maintenance': [[7, 9]], 'jobs': [{'start': 2, 'end': 8, 'units': 1}, {'start': 4, 'end': 12, 'units': 2}], 'capacity': 2, 'query': {'ready': 0, 'duration': 4, 'units': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'profile': [[0, 20, 0]], 'available_unit_minutes': 0, 'booking': None}
    assert request == before

def test_continuous_booking_across_several_capacity_levels():
    request = {'horizon': [0, 20], 'open': [[0, 20]], 'maintenance': [], 'jobs': [{'start': 2, 'end': 10, 'units': 1}, {'start': 5, 'end': 8, 'units': 1}], 'capacity': 3, 'query': {'ready': 1, 'duration': 14, 'units': 1}}
    before = copy.deepcopy(request)
    assert run(request) == {'profile': [[0, 2, 3], [2, 5, 2], [5, 8, 1], [8, 10, 2], [10, 20, 3]], 'available_unit_minutes': 49, 'booking': [1, 15]}
    assert request == before

def test_small_calendar_against_minute_occupancy():
    import random
    rng = random.Random(1102)
    for _ in range(80):
        def interval():
            return sorted(rng.sample(range(-2, 15), 2))
        request = dict(horizon=[0, 12], capacity=rng.randint(1, 4),
                       open=[interval() for _ in range(3)],
                       maintenance=[interval() for _ in range(2)],
                       jobs=[dict(zip(("start", "end", "units"), [*interval(), rng.randint(1, 3)]))
                             for _ in range(3)],
                       query=dict(ready=rng.randint(-1, 12), duration=rng.randint(1, 6),
                                  units=rng.randint(1, 4)))
        before = copy.deepcopy(request)
        cells = []
        for minute in range(12):
            opened = sum(minute in range(a, b) for a, b in request["open"]) > 0
            closed = sum(minute in range(a, b) for a, b in request["maintenance"]) > 0
            busy = sum(j["units"] for j in request["jobs"] if minute in range(j["start"], j["end"]))
            cells.append(max(0, request["capacity"] - busy) if opened and not closed else 0)
        profile = []
        for minute, free in enumerate(cells):
            if profile and profile[-1][2] == free:
                profile[-1][1] += 1
            else:
                profile.append([minute, minute + 1, free])
        q = request["query"]
        starts = [start for start in range(max(0, q["ready"]), 13-q["duration"])
                  if min(cells[start:start+q["duration"]]) >= q["units"]]
        booking = [starts[0], starts[0]+q["duration"]] if starts else None
        assert run(request) == dict(profile=profile, available_unit_minutes=sum(cells), booking=booking)
        assert request == before
