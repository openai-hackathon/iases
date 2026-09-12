"""Interval aggregation for factory analytics."""
from datetime import datetime
from collections.abc import Iterable

def covered_seconds(intervals: Iterable[tuple[datetime, datetime]]) -> float:
    """Return the time covered by already-clipped, positive intervals."""
    ordered = sorted(intervals)
    if not ordered:
        return 0.0
    left, right = ordered[0]
    total = 0.0
    for start, end in ordered[1:]:
        if start <= right:
            right = max(right, end)
        else:
            total += (right - left).total_seconds()
            left, right = start, end
    return total + (right - left).total_seconds()
