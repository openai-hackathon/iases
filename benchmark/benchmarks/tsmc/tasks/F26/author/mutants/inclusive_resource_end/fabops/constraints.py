"""Global physical and routing feasibility of an event interpretation."""
def admissible(events, pairs, request):
    by_id = {event["id"]: event for event in events}
    intervals = [(by_id[start], by_id[end]) for start, end in pairs]
    for start, end in intervals:
        low, high = request.get("duration_limits", {}).get(start["activity"], [0, float("inf")])
        if not low <= end["time"] - start["time"] <= high:
            return False
    for resource, capacity in request.get("capacities", {}).items():
        points = sorted({event["time"] for pair in intervals for event in pair})
        for tick in points:
            usage = sum(start.get("units", 1) for start, end in intervals
                        if start["resource"] == resource and start["time"] <= tick <= end["time"])
            if usage > capacity:
                return False
    for earlier, later in request.get("route", []):
        for a, b in intervals:
            for c, d in intervals:
                if a["case"] == c["case"] and a["activity"] == earlier and c["activity"] == later:
                    if b["time"] > c["time"]:
                        return False
    # Pairs of event IDs express coupled audit evidence, not transport duplicates.
    chosen = {identifier for pair in pairs for identifier in pair}
    for left, right in request.get("coupled", []):
        if (left in chosen) != (right in chosen):
            return False
    return True
