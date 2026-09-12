"""Reproducible downtime reports over explicitly selected input windows."""
from collections.abc import Iterable, Mapping
from typing import Any
from .timeutil import timestamp
from .intervals import covered_seconds

def downtime_seconds(
    events: Iterable[Mapping[str, Any]], machine_id: str,
    window_start: str, window_end: str,
) -> float:
    left, right = timestamp(window_start), timestamp(window_end)
    if right <= left:
        raise ValueError("window_end must be after window_start")
    intervals = []
    for event in events:
        if event["machine_id"] != machine_id:
            continue
        start = timestamp(event["start"])
        end = right if event["end"] is None else timestamp(event["end"])
        # A still-open event may start after the requested historical window.
        if event["end"] is not None and end < start:
            raise ValueError("event end must not precede event start")
        clipped_start, clipped_end = max(left, start), min(right, end)
        if clipped_start < clipped_end:
            intervals.append((clipped_start, clipped_end))
    return float(covered_seconds(intervals))

def make_report(events, machine_id, window_start, window_end):
    total = (timestamp(window_end) - timestamp(window_start)).total_seconds()
    down = downtime_seconds(events, machine_id, window_start, window_end)
    return {
        "schema_version": "1.0",
        "machine_id": machine_id,
        "window_start": window_start,
        "window_end": window_end,
        "window_seconds": total,
        "downtime_seconds": down,
        "downtime_fraction": down / total,
    }
