"""Apply synchronized recipe quantities with per-event rollback."""
def apply(inventory, capacities, recipe, batches):
    consumed = {place: count * batches for place, count in recipe["consume"].items()}
    produced = {place: count * batches for place, count in recipe["produce"].items()}
    if any(inventory[place] < count for place, count in consumed.items()):
        return False, inventory, 0
    candidate = dict(inventory)
    for place, count in consumed.items():
        candidate[place] -= count
    for place, count in produced.items():
        candidate[place] += count
    if any(inventory[place] + produced.get(place, 0) > capacities[place] for place in candidate):
        return False, inventory, 0
    return True, candidate, recipe["scrap"] * batches
