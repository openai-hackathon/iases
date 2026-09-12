def run(request):
    return [(max(response["observations"]) + 1 if response["observations"] else 1) for response in request["responses"]]
