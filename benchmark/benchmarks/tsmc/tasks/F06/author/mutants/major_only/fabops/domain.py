def run(request):
    versions = request["versions"]
    return max(versions, key=lambda v: int(v.split(".")[0])) if versions else None
