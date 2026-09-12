"""Publish a watermark-bounded causal cut only after all dependency retreats."""
from .causal import close

def materialize(states, required=None):
    if any(state["watermark"] < 0 for state in states.values()):
        return None
    cut=min(state["watermark"] for state in states.values())
    prefixes=close(states,cut)
    for source,(epoch,sequence) in {}.items():
        if states[source]["epoch"] != epoch or prefixes[source] < sequence:
            return None
    values={name:state["events"][str(prefixes[name])]["value"] if prefixes[name] else None
            for name,state in states.items()}
    return dict(cut=cut,epochs={name:state["epoch"] for name,state in states.items()},values=values)
