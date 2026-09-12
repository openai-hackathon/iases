import math
def run(request):
    values = sorted(request["values"])
    index = min(len(values) - 1, int(request["q"] * len(values)))
    return values[index] if values else None
