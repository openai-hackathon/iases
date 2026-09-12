"""Search full markings, retaining globally minimal conformance witnesses."""
import heapq
from .net import fire

def replay(request):
    places = sorted(request["capacities"])
    initial = tuple(request["initial"].get(p, 0) for p in places)
    final = tuple(request["final"].get(p, 0) for p in places)
    trace = request["trace"]
    queue = [(0, (), 0, initial)]
    best = {(0, initial): (0, ())}
    while queue:
        silent, path, index, marking = heapq.heappop(queue)
        if best.get((index, marking)) != (silent, path):
            continue
        if index == len(trace) and marking == final:
            return dict(accepted=True, witness=list(path), silent=silent,
                        marking=dict(zip(places, marking)))
        for item in sorted(request["transitions"], key=lambda item: item["id"]):
            hidden = item["label"] is None
            if not hidden and (index == len(trace) or item["label"] != trace[index]):
                continue
            changed = fire(marking, item, places, request["capacities"])
            if changed is None:
                continue
            target = (index + int(not hidden), changed)
            score = (silent + int(hidden), path + (item["id"],))
            if target not in best or score < best[target]:
                best[target] = score
                heapq.heappush(queue, (*score, *target))
                if not hidden:
                    break
    return dict(accepted=False, witness=[], silent=None,
                marking=dict(zip(places, initial)))
