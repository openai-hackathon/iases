def run(request):
    return [max(1, response["nextSequence"] - 1) for response in request["responses"]]
