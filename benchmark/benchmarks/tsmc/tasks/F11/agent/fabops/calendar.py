"""Translate operating windows and reservations to available capacity."""
def capacity_profile(request):
    start, end = request["horizon"]
    result = []
    for a, b in sorted(request["open"]):
        left, right = max(start, a), min(end, b)
        if left >= right:
            continue
        unavailable = sum(max(0, min(right, y) - max(left, x))
                          for x, y in request["maintenance"])
        used = sum(job["units"] for job in request["jobs"]
                   if job["start"] < right and job["end"] > left)
        effective_end = max(left, right - unavailable)
        result.append([left, effective_end, max(0, request["capacity"] - used)])
    return result
