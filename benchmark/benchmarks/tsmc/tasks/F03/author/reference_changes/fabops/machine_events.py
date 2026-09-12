"""Latest known state per machine from an event feed."""
import copy
class ConflictError(ValueError): pass
ALLOWED={"AVAILABLE","BUSY","MAINTENANCE","LOCKED"}

def reduce_events(events, initial=None):
    state=copy.deepcopy(initial or {})
    for e in events:
        if type(e["sequence"]) is not int or e["sequence"]<0 or e["new_state"] not in ALLOWED:
            raise ValueError("invalid machine event")
        current={"sequence":e["sequence"], "state":e["new_state"]}
        previous=state.get(e["machine_id"])
        if previous is not None:
            if e["sequence"] < previous["sequence"]:
                continue
            if e["sequence"] == previous["sequence"]:
                if e["new_state"] != previous["state"]:
                    raise ConflictError("conflicting event at current sequence")
                continue
        state[e["machine_id"]]=current
    return state

def run(data): return reduce_events(data["events"],data.get("initial"))
