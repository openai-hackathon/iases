def run(request):
    return max(0, request["wall_end"] - request["wall_start"])
