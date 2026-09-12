def run(request):
    cursor = request["cursor"]
    acknowledgements = set(request["acks"])
    cursor = max(acknowledgements | {cursor})
    return cursor
