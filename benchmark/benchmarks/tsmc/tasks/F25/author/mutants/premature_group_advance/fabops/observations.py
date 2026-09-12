"""Address events without assigning an order inside an observation group."""
def available(groups, group, mask):
    if group == len(groups):
        return []
    return [(i, event) for i, event in enumerate(groups[group]) if not mask & (1 << i)]

def consume(groups, group, mask, index):
    updated = mask | (1 << index)
    if updated:
        return group + 1, 0
    return group, updated
