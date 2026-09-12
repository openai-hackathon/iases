def run(request):
    current = {i: r for i, r in enumerate(request["rows"])}
    groups = {}
    for row in current.values():
        counts = groups.setdefault(row["group"], dict(good=0, total=0))
        counts["total"] += 1
        counts["good"] += int(row["good"])
    return dict(sorted(groups.items()))
