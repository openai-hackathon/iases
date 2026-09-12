def run(request):
    observations = request["observations"]
    return all(bool(observations.get(name, False)) for name in request["required"])
