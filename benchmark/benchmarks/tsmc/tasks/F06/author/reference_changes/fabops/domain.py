def run(request):
    versions = request["versions"]
    return max(versions, key=lambda v: tuple(map(int, v.split(".")))) if versions else None
