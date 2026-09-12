"""Translate operating windows and reservations to available capacity."""
def capacity_profile(request):
    start, end = request["horizon"]
    intervals = request["open"] + request["maintenance"]
    boundaries = {start, end}
    for left, right in intervals:
        boundaries.update((max(start, min(end, left)), max(start, min(end, right))))
    for job in request["jobs"]:
        boundaries.update((max(start, min(end, job["start"])),
                           max(start, min(end, job["end"]))))
    ordered = sorted(boundaries)
    result = []
    for left, right in zip(ordered, ordered[1:]):
        opened = any(a <= left < b for a, b in request["open"][:1])
        closed = any(a <= left < b for a, b in request["maintenance"])
        used = sum(job["units"] for job in request["jobs"]
                   if job["start"] <= left < job["end"])
        free = max(0, request["capacity"] - used) if opened and not closed else 0
        if result and result[-1][2] == free:
            result[-1][1] = right
        else:
            result.append([left, right, free])
    return result
