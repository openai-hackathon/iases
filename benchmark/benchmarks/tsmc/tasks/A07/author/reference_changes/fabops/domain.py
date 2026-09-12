def run(request):
    values = [v for v in request["values"] if v is not None]
    return sum(values) / len(values) if values else None
