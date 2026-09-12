def run(request):
    expired = request["now"] >= request["ttl"]
    return None if expired else request["value"]
