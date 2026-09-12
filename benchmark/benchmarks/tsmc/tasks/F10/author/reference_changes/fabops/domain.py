def run(request):
    observations = request["observations"]
    return all(observations.get(name, False) is True for name in request["required"])
