"""Find a complete feasible internal ordering before committing a material bundle."""
from .ledger import apply

def groups(events):
    grouped = {}
    for event in events:
        key = ("bundle", event["bundle"]) if "bundle" in event else ("event", event["id"])
        grouped.setdefault(key, []).append(event)
    return sorted(grouped.values(), key=lambda group: min((e["id"], e["order"]) for e in group))

def settle(events, inventory, capacities, recipes, accepted):
    events = sorted(events, key=lambda e: e["id"])
    def search(remaining, state, done, loss, witness):
        if not remaining:
            return state, loss, witness
        for index, event in enumerate(remaining):
            if not set(event.get("after", [])) <= done:
                continue
            ok, candidate, scrap = apply(state, capacities, recipes[event["recipe"]], event["batches"])
            if not ok:
                continue
            result = search(remaining[:index] + remaining[index+1:], candidate,
                            done | {event["id"]}, loss + scrap, witness + [event["id"]])
            if result is not None:
                return result
        return None
    return search(events, dict(inventory), set(accepted), 0, [])
