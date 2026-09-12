def run(request):
    return sum(e["quantity"] if e["type"] == "receipt" else e["quantity"] for e in request["events"])
