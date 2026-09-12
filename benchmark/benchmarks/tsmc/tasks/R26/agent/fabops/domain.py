def run(request):
    responses = {key: row["value"] for key, row in zip(request["ids"], request["responses"])}
    return [responses.get(key) for key in request["ids"]]
