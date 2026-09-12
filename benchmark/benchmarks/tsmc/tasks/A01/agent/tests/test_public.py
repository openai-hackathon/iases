import pytest
from fabops.analytics import downtime_seconds, make_report
S = "2026-01-15T00:00:00Z"
E = "2026-01-15T01:00:00Z"
def event(start, end):
    return {"event_id": "a", "machine_id": "M-01", "start": start, "end": end}
def test_empty():
    assert downtime_seconds([], "M-01", S, E) == 0.0
def test_single_interval():
    assert downtime_seconds([event(S, "2026-01-15T00:10:00Z")], "M-01", S, E) == 600
def test_report_schema():
    report = make_report([], "M-01", S, E)
    assert report["schema_version"] == "1.0"
    assert report["window_seconds"] == 3600
    assert report["downtime_fraction"] == 0.0
def test_invalid_window():
    with pytest.raises(ValueError):
        downtime_seconds([], "M-01", E, S)
def test_touching_intervals():
    mid = "2026-01-15T00:30:00Z"
    assert downtime_seconds([event(S, mid), event(mid, E)], "M-01", S, E) == 3600

import json, subprocess, sys
from pathlib import Path

def test_public_cli_fixture():
    p=subprocess.run([sys.executable,"-m","fabops","--input","data/request.json"],capture_output=True,text=True,timeout=10,check=True)
    assert json.loads(p.stdout)==json.loads(Path("data/expected.json").read_text())

def test_public_overlap_repro():
    events=[event("2026-01-15T00:10:00Z","2026-01-15T00:25:00Z"),event("2026-01-15T00:20:00Z","2026-01-15T00:35:00Z")]
    assert downtime_seconds(events,"M-01",S,E)==1500
