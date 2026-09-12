def run(request):
    responses = {r["id"]: r["value"] for r in request["responses"]}
    return [responses.get(key) for key in request["ids"]]
