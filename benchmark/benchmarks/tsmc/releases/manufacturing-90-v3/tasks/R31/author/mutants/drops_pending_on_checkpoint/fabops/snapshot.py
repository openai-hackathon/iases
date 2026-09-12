"""Materialize a time cut that every source can certify as complete."""
def materialize(states):
    watermarks = [state["watermark"] for state in states.values()]
    if any(value < 0 for value in watermarks):
        return None
    cut = min(watermarks)
    values = {}
    for source, state in states.items():
        eligible = [event for event in state["events"].values()
                    if event["sequence"] < state["next"] and event["time"] <= cut]
        latest = max(eligible, key=lambda event: event["sequence"], default=None)
        values[source] = latest["value"] if latest is not None else None
    return dict(cut=cut, epochs={source: state["epoch"] for source, state in states.items()}, values=values)
