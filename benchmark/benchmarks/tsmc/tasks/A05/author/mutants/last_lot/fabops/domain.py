def run(request):
    lots = request["lots"]
    return lots[-1]["good"] / lots[-1]["tested"] if lots else None
