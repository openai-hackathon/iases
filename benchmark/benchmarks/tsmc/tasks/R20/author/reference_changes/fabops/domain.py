def run(request):
    return [type(value) is int and 1 <= value <= 300 for value in request["timeouts"]]
