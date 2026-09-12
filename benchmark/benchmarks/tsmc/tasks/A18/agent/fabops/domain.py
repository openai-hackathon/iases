def run(request):
    output = []
    for time in request["queries"]:
        candidates = [r for r in request["readings"] if r[0] - time <= request["tolerance"]]
        nearest = min(candidates, key=lambda r: (abs(r[0] - time), r[0])) if candidates else None
        output.append(nearest[1] if nearest else None)
    return output
