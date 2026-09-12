"""Publish exact window values and compensating retractions for changed results."""
from fractions import Fraction as F
from .integrate import measure

def summarize(window, pressure, flow, minimum):
    start, end = F(window["start"]), F(window["end"])
    covered, volume, work = measure(pressure, flow, start, end)
    coverage = min(sum(max(F(0), min(end, row[1]) - max(start, row[0])) for row in pressure),
                   sum(max(F(0), min(end, row[1]) - max(start, row[0])) for row in flow)) / (end - start)
    accepted = covered > 0 and coverage >= F(minimum)
    return dict(id=window["id"], coverage=str(coverage), accepted=accepted,
                volume=str(volume) if accepted else None,
                work=str(work) if accepted else None)

def changes(previous, current):
    events = []
    for key in sorted(current):
        old, new = previous.get(key), current[key]
        if old == new:
            continue
        if old is not None:
            events.append(dict(op="retract", value=old))
        events.append(dict(op="upsert", value=new))
    return events
