def run(request):
    cursor = request["cursor"]
    acknowledgements = set(request["acks"])
    if cursor + 1 in acknowledgements:
        cursor += 1
    return cursor
