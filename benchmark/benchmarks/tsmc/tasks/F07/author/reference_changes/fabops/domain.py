def run(request):
    route = request["route"]
    position = request["completed"]
    return route[position] if position < len(route) else None
