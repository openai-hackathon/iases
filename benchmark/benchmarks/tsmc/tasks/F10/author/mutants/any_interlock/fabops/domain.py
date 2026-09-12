def run(request):
    observations = request["observations"]
    return any(observations.get(name, False) is True for name in request["required"])
