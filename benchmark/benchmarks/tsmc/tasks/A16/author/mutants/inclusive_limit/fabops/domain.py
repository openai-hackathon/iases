import statistics
def run(request):
    baseline = request["baseline"]
    center = statistics.mean(baseline)
    width = request["k"] * statistics.stdev(baseline)
    return [abs(value - center) >= width for value in request["measurements"]]
