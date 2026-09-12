"""Legacy per-operation validation misses competing lifecycle explanations."""
def admissible(events, pairs, request):
    by_id = {event["id"]: event for event in events}
    for start_id, end_id in pairs:
        start, end = by_id[start_id], by_id[end_id]
        low, high = request.get("duration_limits", {}).get(start["activity"], [0, float("inf")])
        if not low <= end["time"] - start["time"] <= high:
            return False
    return True
