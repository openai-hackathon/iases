import math
def run(request):
    values = sorted(request["values"])
    index = int(request["q"] * max(0, len(values) - 1))
    return values[index] if values else None
