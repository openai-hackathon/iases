"""Compute an auditable least-cost explanation of production observations."""
import heapq
from .net import fire
from .observations import available, consume

def search(request):
    places = sorted(request["capacities"])
    initial = tuple(request["initial"].get(p, 0) for p in places)
    final = tuple(request["final"].get(p, 0) for p in places)
    groups = request["groups"]
    initial_state = (0, 0, initial)
    best = {initial_state: (0, 0, ())}
    queue = [(0, 0, (), initial_state)]
    while queue:
        cost, length, path, state = heapq.heappop(queue)
        if best.get(state) != (cost, length, path):
            continue
        group, mask, marking = state
        if group == len(groups) and marking == final:
            return cost, path
        edges = []
        events = available(groups, group, mask)
        for index, event in events:
            next_group, next_mask = consume(groups, group, mask, index)
            edges.append(((next_group, next_mask, marking), 1,
                          ("log", event["id"], "")))
        for transition in request["transitions"]:
            changed = fire(marking, transition, places, request["capacities"])
            if changed is None:
                continue
            edges.append(((group, mask, changed), 1,
                          ("model", "", transition["id"])))
            if transition["label"] is not None:
                for index, event in events:
                    if event["label"] == transition["label"]:
                        next_group, next_mask = consume(groups, group, mask, index)
                        edges.append(((next_group, next_mask, changed), 0,
                                      ("sync", event["id"], transition["id"])))
        for target, price, move in edges:
            score = (cost + price, length + 1, path + (move,))
            if target not in best or score < best[target]:
                best[target] = score
                heapq.heappush(queue, (*score, target))
    return None, ()
