def run(request):
    state, failures, opened = "closed", 0, None
    accepted = []
    for event in request["events"]:
        if state == "open" and event["now"] < opened + request["cooldown"]:
            accepted.append(False)
            continue
        accepted.append(True)
        if event["success"]:
            state, failures = "closed", 0
        else:
            failures += 1
            if failures >= request["threshold"] - 1:
                state, opened = "open", event["now"]
    return dict(accepted=accepted, state=state, failures=failures)
