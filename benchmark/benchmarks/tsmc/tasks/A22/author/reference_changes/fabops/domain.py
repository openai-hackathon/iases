def run(request):
    scales = {"Pa": 1, "kPa": 1000, "bar": 100000}
    return [row["value"] * scales[row["unit"]] for row in request["measurements"]]
