"""Compute the greatest dependency-closed vector under certified source cuts."""
def close(states, cut):
    prefixes = {name:max([0]+[event["sequence"] for event in state["events"].values()
                             if event["sequence"] < state["next"] and event["time"] <= cut])
                for name,state in states.items()}
    while True:
        candidate=dict(prefixes)
        for source,state in states.items():
            for sequence in range(1,prefixes[source]+1):
                event=state["events"][str(sequence)]
                for dependency,epoch,required in event.get("depends",[]):
                    if states[dependency]["epoch"] != epoch or prefixes[dependency] < required:
                        candidate[source]=min(candidate[source],sequence-1)
        if candidate == prefixes:
            return prefixes
        return candidate
