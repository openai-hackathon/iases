def run(request):
    current, active, approvals, results = None, None, set(), []
    for event in request["events"]:
        if event["op"] == "edit":
            current = event["revision"]
            approvals.clear()
        elif event["op"] == "approve":
            if event["role"] in request["roles"]:
                approvals.add(event["role"])
        elif event["op"] == "revoke":
            approvals.discard(event["role"])
        else:
            valid = current is not None and set(request["roles"]) <= approvals
            if valid:
                active = current
            results.append(valid)
    return dict(activations=results, active=active)
