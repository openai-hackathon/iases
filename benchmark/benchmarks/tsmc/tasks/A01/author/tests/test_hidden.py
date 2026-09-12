"""Author-only assessment cases. Never stage these during agent execution."""
import copy
import json
import random
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from fabops.analytics import downtime_seconds, make_report

START = datetime(2026, 1, 15, tzinfo=timezone.utc)
S, E = START.isoformat(), (START + timedelta(hours=1)).isoformat()
def ts(seconds):
    return (START + timedelta(seconds=seconds)).isoformat()
def ev(start, end, machine="M-01", eid="x"):
    return {"event_id": eid, "machine_id": machine, "start": ts(start),
            "end": None if end is None else ts(end)}
def run(rows, machine="M-01", start=S, end=E):
    return downtime_seconds(rows, machine, start, end)

def test_overlap_union():
    assert run([ev(600, 1500), ev(1200, 2100)]) == 1500
def test_nested_interval():
    assert run([ev(100, 500), ev(200, 300)]) == 400
def test_duplicate_invariance():
    rows = [ev(100, 500)]
    assert run(rows + copy.deepcopy(rows)) == run(rows)
def test_clipped_overlap():
    assert run([ev(-600, 600), ev(0, 1200)]) == 1200
def test_unsorted_bridge():
    assert run([ev(1800, 2400), ev(600, 1500), ev(1200, 2100)]) == 1800
def test_machine_isolation_with_overlap():
    rows = [ev(600, 1500), ev(1200, 2100), ev(0, 3600, "M-02")]
    assert run(rows) == 1500
def test_offset_equivalence():
    a = ev(600, 1500)
    b = {"event_id": "b", "machine_id": "M-01",
         "start": "2026-01-15T08:20:00+08:00",
         "end": "2026-01-15T08:35:00+08:00"}
    assert run([a, b]) == 1500
def test_report_from_recomputed_program():
    result = make_report([ev(600, 1500), ev(1200, 2100)], "M-01", S, E)
    assert result["downtime_seconds"] == 1500
    assert result["downtime_fraction"] == pytest.approx(5/12, abs=1e-9)
def test_generated_integer_oracle():
    # Independent oracle uses occupied seconds, not the reference sort/merge.
    rng = random.Random(73019)
    for _ in range(30):
        pairs = [(0, 300), (100, 250)]
        pairs.extend((a, a + rng.randrange(1, 200))
                     for a in [rng.randrange(-100, 500) for _ in range(12)])
        rows = [ev(a, b) for a, b in pairs]
        rng.shuffle(rows)
        occupied = set()
        for a, b in pairs:
            occupied.update(range(max(0, a), min(600, b)))
        assert run(rows, end=ts(600)) == len(occupied)

def test_disjoint_regression():
    assert run([ev(0, 100), ev(200, 300)]) == 200
def test_empty_regression():
    assert run([]) == 0.0
def test_touching_regression():
    assert run([ev(0, 100), ev(100, 200)]) == 200
def test_open_end_regression():
    assert run([ev(3000, None)]) == 600
def test_zero_length_regression():
    assert run([ev(100, 100)]) == 0
def test_outside_window_regression():
    assert run([ev(-100, -10), ev(4000, None)]) == 0
def test_input_not_mutated():
    rows = [ev(10, 100), ev(200, 300)]
    before = copy.deepcopy(rows)
    run(rows)
    assert rows == before
def test_invalid_window_regression():
    with pytest.raises(ValueError):
        run([], start=E, end=S)
def test_naive_time_regression():
    with pytest.raises(ValueError):
        run([], start="2026-01-15T00:00:00")
def test_reversed_event_regression():
    with pytest.raises(ValueError):
        run([ev(200, 100)])

import json, subprocess, sys
from pathlib import Path

def test_hidden_cli_fixture():
    root=Path(__file__).parent.parent / "data"
    p=subprocess.run([sys.executable,"-m","fabops","--input",str(root/"request.json")],capture_output=True,text=True,timeout=10,check=True)
    assert json.loads(p.stdout)==json.loads((root/"expected.json").read_text())
