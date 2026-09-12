def run(request):
    active = request["initial"]
    states = []
    for value in request["values"]:
        if not active and value >= request["high"]:
            active = True
        elif active and value < request["low"]:
            active = False
        states.append(active)
    return states
