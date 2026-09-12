def run(request):
    lots = request["lots"]
    return sum(lot["good"] / lot["tested"] for lot in lots) / len(lots) if lots else None
