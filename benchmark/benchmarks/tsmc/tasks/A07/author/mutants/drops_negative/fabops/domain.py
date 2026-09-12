def run(request):
    values = [v for v in request["values"] if v is not None and v >= 0]
    return sum(values) / len(values) if values else None
