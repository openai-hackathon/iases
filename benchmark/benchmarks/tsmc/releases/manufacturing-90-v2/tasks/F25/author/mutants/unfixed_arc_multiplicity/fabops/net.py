"""Fire a weighted transition against a bounded marking atomically."""
def fire(marking, transition, places, capacities):
    current = dict(zip(places, marking))
    if any(current[p] < 1 for p, count in transition["consume"].items()):
        return None
    result = dict(current)
    for p, count in transition["consume"].items():
        result[p] -= count
    for p, count in transition["produce"].items():
        result[p] += count
    if any(result[p] > capacities[p] for p in places):
        return None
    return tuple(result[p] for p in places)
