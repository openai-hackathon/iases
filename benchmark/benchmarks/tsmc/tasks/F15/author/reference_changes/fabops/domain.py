def run(request):
    position, retries, state = 0, 0, "active"
    route = request["route"]
    for passed in request["events"]:
        if state != "active" or position == len(route):
            break
        if passed:
            position += 1
            retries = 0
        else:
            retries += 1
            if retries > request["max_retries"]:
                state = "scrap"
    if state == "active" and position == len(route):
        state = "done"
    return dict(state=state, step=route[position] if state == "active" else None, retries=retries)
