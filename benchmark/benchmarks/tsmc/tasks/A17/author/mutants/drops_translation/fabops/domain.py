def run(request):
    output = []
    for x, y in request["points"]:
        for _ in range(request["turns"] % 4):
            x, y = -y, x
        output.append([x, y])
    return output
