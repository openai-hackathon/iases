"""Retain every maximum-cardinality lifecycle interpretation."""
def compatible(start, end):
    return (all(start[key] == end[key] for key in ("case", "activity", "resource"))
            and start["time"] <= end["time"]
            and (start.get("run") is None or end.get("run") is None
                 or start["run"] == end["run"]))

def matchings(events):
    starts = [event for event in events if event["kind"] == "start"]
    ends = [event for event in events if event["kind"] == "complete"]
    best, results = -1, []
    def visit(index, used, pairs):
        nonlocal best, results
        if index == len(starts):
            if len(pairs) > best:
                best, results = len(pairs), []
            if len(pairs) == best:
                results.append(tuple(sorted(pairs)))
            return
        start = starts[index]
        visit(index + 1, used, pairs)
        for end in ends:
            if end["id"] in used or not compatible(start, end):
                continue
            visit(index + 1, used | {end["id"]}, pairs + [(start["id"], end["id"])])
    visit(0, set(), [])
    return results
