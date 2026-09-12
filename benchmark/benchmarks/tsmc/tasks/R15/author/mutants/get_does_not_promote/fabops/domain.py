from collections import OrderedDict
def run(request):
    cache = OrderedDict()
    for operation in request["operations"]:
        key = operation["key"]
        if operation["op"] == "get":
            if key in cache:
                pass
        else:
            weight = operation["weight"]
            if weight > request["capacity"]:
                continue
            cache.pop(key, None)
            cache[key] = weight
            while sum(cache.values()) > request["capacity"]:
                cache.popitem(last=False)
    return dict(keys=list(cache), weight=sum(cache.values()))
