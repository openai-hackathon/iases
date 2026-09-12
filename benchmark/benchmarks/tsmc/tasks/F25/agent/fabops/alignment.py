"""Compute an auditable least-cost explanation of production observations."""
from .net import fire
from .observations import available, consume

def search(request):
    places = sorted(request["capacities"])
    marking = tuple(request["initial"].get(p, 0) for p in places)
    final = tuple(request["final"].get(p, 0) for p in places)
    group, mask, cost, path = 0, 0, 0, ()
    seen = set()
    while (group, mask, marking) not in seen:
        seen.add((group, mask, marking))
        if group == len(request["groups"]) and marking == final:
            return cost, path
        choices = []
        events = available(request["groups"], group, mask)
        for transition in request["transitions"]:
            changed = fire(marking, transition, places, request["capacities"])
            if changed is None:
                continue
            choices.append((transition["model_cost"], ("model", "", transition["id"]),
                            group, mask, changed))
            for index, event in events:
                if transition["label"] is not None and event["label"] == transition["label"]:
                    g, m = consume(request["groups"], group, mask, index)
                    choices.append((0, ("sync", event["id"], transition["id"]), g, m, changed))
        for index, event in events:
            g, m = consume(request["groups"], group, mask, index)
            choices.append((event["skip_cost"], ("log", event["id"], ""), g, m, marking))
        if not choices:
            break
        price, move, group, mask, marking = min(choices)
        cost += price
        path += (move,)
    return None, ()
