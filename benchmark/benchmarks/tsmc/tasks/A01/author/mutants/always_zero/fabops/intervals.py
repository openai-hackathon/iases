"""Interval aggregation for factory analytics."""
from datetime import datetime
from collections.abc import Iterable

def covered_seconds(intervals: Iterable[tuple[datetime, datetime]]) -> float:
    """Return the time covered by already-clipped, positive intervals."""
    return 0.0
