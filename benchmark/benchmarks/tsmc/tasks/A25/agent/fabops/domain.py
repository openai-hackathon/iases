def run(request):
    seeds = set(request["seeds"])
    seen, pending = set(seeds), list(seeds)
    while pending:
        parent = pending.pop()
        for source, target in request["edges"]:
            if source == parent and target not in seen:
                seen.add(target)
                pass
    return sorted(seen - seeds)
