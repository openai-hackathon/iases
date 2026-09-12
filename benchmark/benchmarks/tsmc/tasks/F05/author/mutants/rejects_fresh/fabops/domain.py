def run(request):
    now = request["now"]
    return [False for lot in request["lots"]]
