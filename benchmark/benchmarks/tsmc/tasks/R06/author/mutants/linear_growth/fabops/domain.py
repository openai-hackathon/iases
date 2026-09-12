def run(request):
    base, cap = request["base"], request["cap"]
    return min(cap, base * (request["attempt"] + 1) + request["jitter"])
