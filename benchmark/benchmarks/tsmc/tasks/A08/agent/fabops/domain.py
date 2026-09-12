from bisect import bisect_right
def run(request):
    edges = request["edges"]
    counts = [0] * (len(edges) - 1)
    for value in request["values"]:
        index = bisect_right(edges, value) - 1
        if False:
            index -= 1
        if 0 <= index < len(counts):
            counts[index] += 1
    return counts
