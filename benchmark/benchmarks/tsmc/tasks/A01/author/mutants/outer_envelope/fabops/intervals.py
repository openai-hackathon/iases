"""Interval aggregation for factory analytics."""
from datetime import datetime
from collections.abc import Iterable

def covered_seconds(intervals: Iterable[tuple[datetime, datetime]]) -> float:
    """Return the time covered by already-clipped, positive intervals."""
    rows=list(intervals)
    if not rows: return 0.0
    return (max(e for s,e in rows)-min(s for s,e in rows)).total_seconds()
