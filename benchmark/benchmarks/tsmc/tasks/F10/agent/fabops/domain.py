def run(request):
    observations = request["observations"]
    return all(observations.get(name, True) is True for name in request["required"])
