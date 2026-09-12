def run(request):
    lots = request["lots"]
    availability = request["runtime"] / request["planned"]
    ideal_time = sum(lot["total"] * lot["ideal_cycle"] for lot in lots)
    performance = ideal_time / request["runtime"]
    quality = sum(lot["good"] for lot in lots) / sum(lot["total"] for lot in lots)
    return dict(availability=availability, performance=performance, quality=quality, oee=availability * performance * quality)
