def run(request):
    return [isinstance(value, int) and 1 <= value <= 300 for value in request["timeouts"]]
