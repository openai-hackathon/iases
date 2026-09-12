import json
def run(request):
    stored, output = {}, []
    for command in request["commands"]:
        fingerprint = json.dumps([command["method"], "", command["payload"]], sort_keys=True, separators=(",", ":"))
        key = command["key"]
        if key not in stored:
            stored[key] = (fingerprint, command["result"])
        old, result = stored[key]
        output.append(result if old == fingerprint else "conflict")
    return output
