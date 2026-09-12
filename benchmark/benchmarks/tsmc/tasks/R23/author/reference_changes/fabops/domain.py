def run(request):
    return [response["nextSequence"] for response in request["responses"]]
