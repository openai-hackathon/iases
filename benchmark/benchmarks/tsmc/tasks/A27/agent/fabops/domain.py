def run(request):
    versions = {r["effective"]: r["value"] for r in request["changes"]}
    times = list(versions)
    return [dict(start=t, end=times[i + 1] if i + 1 < len(times) else None, value=versions[t])
            for i, t in enumerate(times)]
