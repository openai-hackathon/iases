def run(request):
    latest = {}
    for record in request["records"]:
        key = record["key"]
        if key not in latest or record["version"] > latest[key]["version"]:
            latest[key] = record
    return {k: r["value"] for k, r in sorted(latest.items()) if not r["deleted"]}
