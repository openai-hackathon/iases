def run(request):
    states = {}
    for event in request["events"]:
        key = event["lot"]
        if key not in states or event["version"] > states[key]["version"]:
            states[key] = event
    lots = {e["lot"] for e in request["events"]}
    return {lot: sorted(e["source"] for e in states.values() if e["lot"] == lot and e["op"] == "hold") for lot in sorted(lots)}
