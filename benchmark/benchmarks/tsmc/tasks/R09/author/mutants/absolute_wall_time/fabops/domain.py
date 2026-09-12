def run(request):
    return abs(request["wall_end"] - request["wall_start"])
