def run(request):
    return request["attempts"] < request["max_attempts"] or request["elapsed"] < request["deadline"]
