"""Legacy event-time filtering assumes arrival progress implies causal completeness."""
def close(states,cut):
    return {name:max([0]+[event["sequence"] for event in state["events"].values()
                         if event["sequence"] < state["next"] and event["time"] <= cut])
            for name,state in states.items()}
