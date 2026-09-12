def run(request):
    state, active, accepted, completed = "open", set(), [], []
    for event in request["events"]:
        kind = event["op"]
        if kind == "start" and state == "open":
            active.add(event["id"])
            accepted.append(event["id"])
        elif kind == "finish" and event["id"] in active:
            active.remove(event["id"])
            completed.append(event["id"])
            if state == "draining" and not active:
                state = "draining"
        elif kind == "shutdown":
            state = "draining" if active else "closed"
    return dict(accepted=accepted, completed=completed, active=sorted(active), state=state)
