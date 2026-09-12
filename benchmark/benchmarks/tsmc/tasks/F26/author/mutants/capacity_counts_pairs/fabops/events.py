"""Deduplicate transport retries without collapsing simultaneous operations."""
def normalize(events):
    seen = {}
    for event in events:
        identifier = event["id"]
        if identifier in seen and seen[identifier] != event:
            raise ValueError("Conflicting event id")
        seen[identifier] = dict(event)
    return [seen[key] for key in sorted(seen)]
