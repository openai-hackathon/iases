def run(request):
    samples = sorted(request["samples"])
    return sum((b[0] - a[0]) * (a[1] + b[1]) / 2 for a, b in zip(samples, samples[1:]))
