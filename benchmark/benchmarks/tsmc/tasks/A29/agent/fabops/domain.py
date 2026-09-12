"""Reconstruct each recorded-time snapshot, then publish only derived changes."""
from .history import visible
from .support import segments
from .windows import summarize, changes

def run(request):
    output, previous = [], {}
    for asof in request["queries"]:
        samples = visible(request["samples"], asof)
        calibrations = visible(request["calibrations"], asof)
        support = {channel: segments(samples, request["clocks"], calibrations, channel,
                                     request["max_gap"][channel])
                   for channel in ("pressure", "flow")}
        current = {window["id"]: summarize(window, support["pressure"], support["flow"],
                                           request["min_coverage"])
                   for window in request["windows"]}
        output.append(dict(windows=[current[key] for key in sorted(current)],
                           changes=changes(previous, current)))
        previous = current
    return output
