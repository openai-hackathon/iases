def run(request):
    return request["attempts"] <= request["max_attempts"] and request["elapsed"] < request["deadline"]
