def run(request):
    output = []
    for x, y in request["points"]:
        for _ in range(max(0, request["turns"])):
            x, y = -y, x
        output.append([x + request["dx"], y + request["dy"]])
    return output
