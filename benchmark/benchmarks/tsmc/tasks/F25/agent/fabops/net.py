"""Atomic bounded token movement."""
def fire(marking, transition, places, capacities):
    current = dict(zip(places, marking))
    if any(current[p] < n for p, n in transition["consume"].items()):
        return None
    result = tuple(current[p] - int(p in transition["consume"])
                   + int(p in transition["produce"]) for p in places)
    if any(n > capacities[p] for p, n in zip(places, result)):
        return None
    return result
