def run(request):
    return max(0, sum(e["quantity"] if e["type"] == "receipt" else -e["quantity"] for e in request["events"]))
