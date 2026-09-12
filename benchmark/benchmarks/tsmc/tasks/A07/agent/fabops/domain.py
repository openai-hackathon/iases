def run(request):
    values = [0 if v is None else v for v in request["values"]]
    return sum(values) / len(values) if values else None
