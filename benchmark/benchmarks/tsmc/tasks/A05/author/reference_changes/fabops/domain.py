def run(request):
    lots = request["lots"]
    return sum(lot["good"] for lot in lots) / sum(lot["tested"] for lot in lots) if lots else None
