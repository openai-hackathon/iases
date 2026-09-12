"""Select logical event versions before reconstructing material causality."""
def active_events(records):
    seen, latest = {}, {}
    for record in records:
        key = (record["id"], record["revision"])
        if key in seen and seen[key] != record:
            raise ValueError("Conflicting event revision")
        seen[key] = dict(record)
        current = latest.get(record["id"])
        if current is None or record["revision"] != current["revision"]:
            latest[record["id"]] = dict(record)
    active = [event for event in latest.values() if not event.get("deleted", False)]
    return sorted(active, key=lambda event: (event["id"], event["order"]))
