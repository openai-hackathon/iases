def run(request):
    now = request["now"]
    return [now < lot["expires_at"] for lot in request["lots"]]
