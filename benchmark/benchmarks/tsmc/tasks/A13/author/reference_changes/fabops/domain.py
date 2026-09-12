def run(request):
    samples = sorted(request["samples"])
    return sum(b[1] - a[1] if b[1] >= a[1] else b[1] for a, b in zip(samples, samples[1:]))
