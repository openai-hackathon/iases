def run(request):
    totals = dict.fromkeys(request["priority"], 0)
    for minute in range(request["start"], request["end"]):
        for cause in request["priority"]:
            if any(r["cause"] == cause and r["start"] <= minute <= r["end"] for r in request["intervals"]):
                totals[cause] += 1
                break
    return totals
