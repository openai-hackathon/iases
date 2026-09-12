"""Select complete paired windows before averaging any spectra."""
from .preprocess import fill, detrend
from .spectrum import window

def segments(request):
    x = request["samples"]
    y = request.get("reference", x)
    length = request.get("segment_length", len(x))
    step = length
    accepted = []
    for start in range(0, len(x)-length+1, step):
        first, cx = fill(x[start:start+length], request["max_gap"])
        second, cy = fill(y[start:start+length], request["max_gap"])
        if first is None or second is None or min(cx, cy) < request["min_coverage"]:
            continue
        first, slope = detrend(first)
        second, _ = detrend(second)
        first, normalizer = window(first)
        second, _ = window(second)
        accepted.append((start, first, second, slope, normalizer))
    return accepted
