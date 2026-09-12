def run(request):
    route = request["route"]
    position = max(0, request["completed"] - 1)
    return route[position] if position < len(route) else None
