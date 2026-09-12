def run(request):
    start, end = request["start"], request["end"]
    cursor, blocked = start, 0
    for left, right in sorted(request["maintenance"]):
        left, right = max(start, left, cursor), min(end, right)
        blocked += max(0, right - left)
        cursor = max(cursor, right)
    return end - start - blocked
