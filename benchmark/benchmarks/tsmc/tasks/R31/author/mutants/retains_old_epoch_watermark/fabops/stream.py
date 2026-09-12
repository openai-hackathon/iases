"""Track a source's contiguous prefix independently of delivery order."""
import copy

def initial(epoch=0):
    return dict(epoch=epoch, next=1, watermark=-1, events={}, barriers=[])

def accept(previous, page):
    if page["epoch"] < previous["epoch"]:
        return "stale", previous
    state = copy.deepcopy(previous)
    if page["epoch"] > state["epoch"]:
        state = dict(initial(page["epoch"]), watermark=previous["watermark"])
    for event in page["events"]:
        key = str(event["sequence"])
        old = state["events"].get(key)
        if old is not None and old != event:
            return "conflict", previous
        state["events"][key] = dict(event)
    state["barriers"].append([page["through"], page["watermark"]])
    while str(state["next"]) in state["events"]:
        state["next"] += 1
    ready = [watermark for through, watermark in state["barriers"] if through < state["next"]]
    state["watermark"] = max([state["watermark"]] + ready)
    state["barriers"] = [[through, watermark] for through, watermark in state["barriers"] if through >= state["next"]]
    return "accepted", state
