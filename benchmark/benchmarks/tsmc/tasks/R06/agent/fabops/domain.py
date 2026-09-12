def run(request):
    base, cap = request["base"], request["cap"]
    return min(cap, base * 2 ** request["attempt"]) + request["jitter"]
