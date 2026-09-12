def identity(row):
    return row["key"]
def run(request):
    cache = {identity(row): row["value"] for row in request["entries"]}
    return [cache.get(identity(row)) for row in request["queries"]]
