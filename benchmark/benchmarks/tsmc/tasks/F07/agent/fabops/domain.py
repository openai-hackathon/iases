def run(request):
    route = request["route"]
    position = (route.index(route[request["completed"] - 1]) + 1) if request["completed"] else 0
    return route[position] if position < len(route) else None
