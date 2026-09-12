def run(request):
    samples = sorted(request["samples"])
    return sum((a[1] + b[1]) / 2 for a, b in zip(samples, samples[1:]))
