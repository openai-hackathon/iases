def run(request):
    rows = sorted(request["calibrations"], key=lambda r: r["effective"])
    output = []
    for time, value in request["samples"]:
        eligible = [r for r in rows if r["effective"] <= time]
        rule = eligible[0] if eligible else None
        output.append(value * rule["gain"] + rule["offset"] if rule else None)
    return output
