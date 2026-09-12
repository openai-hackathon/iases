def run(request):
    index = {(r["part"], request["stations"][0]): r["value"] for r in request["measurements"]}
    return [dict(part=part, values=[index.get((part, station)) for station in request["stations"]])
            for part in request["parts"]]
