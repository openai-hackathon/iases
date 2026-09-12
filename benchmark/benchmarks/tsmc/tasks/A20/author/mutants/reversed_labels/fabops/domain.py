def run(request):
    return [label == -1 for label in request["labels"]]
