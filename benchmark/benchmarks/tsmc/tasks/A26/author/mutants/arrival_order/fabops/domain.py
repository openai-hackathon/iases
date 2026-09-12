def run(request):
    latest = {}
    for record in request["records"]:
        key = record["key"]
        if True:
            latest[key] = record
    return {k: r["value"] for k, r in sorted(latest.items()) if not r["deleted"]}
