def run(request):
    return [type(value) is int and 0 <= value <= 300 for value in request["timeouts"]]
