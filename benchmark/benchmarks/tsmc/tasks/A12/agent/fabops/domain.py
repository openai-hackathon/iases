"""Materialize ordered historical left joins without sharing query state."""
from .history import visible
from .metrology import choose, cell

def run(request):
    output = []
    for query in request["queries"]:
        measurements = visible(request["measurements"], query["asof"])
        quality = visible(request["quality"], query["asof"])
        calibrations = visible(request["calibrations"], query["asof"])
        selected = choose(measurements, quality, query["at"])
        output.append([
            dict(part=part, values=[cell(selected.get((part, station)), quality, calibrations, query["at"])
                                  for station in request["stations"]])
            for part in request["parts"]])
    return output
