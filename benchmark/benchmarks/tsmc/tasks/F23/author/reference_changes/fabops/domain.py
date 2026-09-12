def run(request):
    pending = {j["id"]: j for j in request["jobs"]}
    schedule, available = {}, {}
    while pending:
        ready = sorted(k for k, j in pending.items() if all(d in schedule for d in j["depends"]))
        if not ready:
            raise ValueError("cyclic dependencies")
        key = ready[0]
        job = pending.pop(key)
        start = max([job["release"], available.get(job["resource"], 0)] + [schedule[d][1] for d in job["depends"]])
        end = start + job["duration"]
        schedule[key] = [start, end]
        available[job["resource"]] = end
    return dict(sorted(schedule.items()))
