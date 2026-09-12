"""Repair short interior holes, retaining observed coverage and least-squares trend."""
def fill(samples, max_gap):
    observed = sum(value is not None for value in samples)
    if samples[0] is None or samples[-1] is None:
        return None, observed / len(samples)
    values = list(samples)
    index = 0
    while index < len(values):
        if values[index] is not None:
            index += 1
            continue
        start = index
        while values[index] is None:
            index += 1
        width = index - start
        if width > max_gap:
            return None, observed / len(samples)
        first, last = values[start - 1], values[index]
        for offset in range(width):
            fraction = (offset + 1) / (width + 1)
            values[start + offset] = first + fraction * (last - first)
    return values, observed / len(samples)

def detrend(values):
    count = len(values)
    middle = (count - 1) / 2
    mean = sum(values) / count
    slope = (sum((index - middle) * (value - mean) for index, value in enumerate(values))
             / sum((index - middle) ** 2 for index in range(count)))
    return [value - mean - slope * (index - middle)
            for index, value in enumerate(values)], slope
