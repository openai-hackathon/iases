def run(request):
    return [response["nextSequence"] + 1 for response in request["responses"]]
