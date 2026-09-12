import math
def run(request):
    values = sorted(request["values"], reverse=True)
    index = max(0, math.ceil(request["q"] * len(values)) - 1)
    return values[index] if values else None
