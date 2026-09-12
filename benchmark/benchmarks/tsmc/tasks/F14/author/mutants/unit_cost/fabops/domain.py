import heapq
def run(request):
    graph = {}
    for source, target, cost in request["edges"]:
        graph.setdefault(source, []).append((target, cost))
    queue = [(0, request["start"])]
    seen = set()
    while queue:
        distance, node = heapq.heappop(queue)
        if node in seen:
            continue
        seen.add(node)
        if node == request["end"]:
            return distance
        for target, cost in graph.get(node, []):
            heapq.heappush(queue, (distance + 1, target))
    return None
