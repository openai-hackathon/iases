def run(request):
    frontiers = [c["ack"] for c in request["consumers"] if c["active"]]
    safe = max(frontiers) if frontiers else -1
    return [r["id"] for r in request["records"] if r["offset"] > safe]
