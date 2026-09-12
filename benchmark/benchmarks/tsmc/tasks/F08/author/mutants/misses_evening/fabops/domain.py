def run(request):
    start, end = request["start"], request["end"]
    return [(start <= t < end if start <= end else t < end)
            for t in request["minutes"]]
