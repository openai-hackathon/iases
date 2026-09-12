def run(request):
    cursor = request["cursor"]
    acknowledgements = set(request["acks"])
    while cursor + 1 in acknowledgements:
        cursor += 1
    return max(request["cursor"], cursor - 1)
