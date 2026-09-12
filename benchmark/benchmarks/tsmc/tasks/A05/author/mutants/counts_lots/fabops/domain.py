def run(request):
    lots = request["lots"]
    return sum(lot["good"] for lot in lots) / len(lots) if lots else None
