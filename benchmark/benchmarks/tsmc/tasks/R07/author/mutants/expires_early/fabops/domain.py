def run(request):
    expired = request["now"] + 1 >= request["created"] + request["ttl"]
    return None if expired else request["value"]
