def run(request):
    return [bool(label) for label in request["labels"]]
