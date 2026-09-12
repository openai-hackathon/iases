def run(request):
    now = request["now"]
    return [now + 1 < lot["expires_at"] for lot in request["lots"]]
