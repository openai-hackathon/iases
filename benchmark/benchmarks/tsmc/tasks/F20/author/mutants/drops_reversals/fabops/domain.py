def run(request):
    return sum(e["quantity"] if e["type"] == "receipt" else 0 for e in request["events"])
