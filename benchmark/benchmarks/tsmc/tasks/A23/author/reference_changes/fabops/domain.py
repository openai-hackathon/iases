def run(request):
    count, mean, m2 = 0, 0.0, 0.0
    for group in request["summaries"]:
        n = group["count"]
        if not n:
            continue
        total = count + n
        delta = group["mean"] - mean
        m2 += group["m2"] + delta * delta * count * n / total
        mean += delta * n / total
        count = total
    return dict(count=count, mean=mean if count else None, variance=m2 / count if count else None)
