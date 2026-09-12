"""Find a complete feasible internal ordering before committing a material bundle."""
from .ledger import apply

def groups(events):
    grouped = {}
    for event in events:
        key = ("bundle", event["bundle"]) if "bundle" in event else ("event", event["id"])
        grouped.setdefault(key, []).append(event)
    return sorted(grouped.values(), key=lambda group: min((e["id"], e["order"]) for e in group))

def settle(events, inventory, capacities, recipes, accepted):
    state, loss, witness = dict(inventory), 0, []
    for event in sorted(events, key=lambda e: e["id"]):
        ok, state, scrap = apply(state, capacities, recipes[event["recipe"]], event["batches"])
        if not ok:
            return None
        loss += scrap
        witness.append(event["id"])
    return state, loss, witness
