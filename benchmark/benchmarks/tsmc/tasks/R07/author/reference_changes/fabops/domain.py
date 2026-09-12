def run(request):
    expired = request["now"] >= request["created"] + request["ttl"]
    return None if expired else request["value"]
