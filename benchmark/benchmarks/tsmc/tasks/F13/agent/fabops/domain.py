def run(request):
    batches = []
    for lot in request["lots"]:
        key = (lot["product"], lot["recipe"])
        for batch in batches:
            if batch["key"] == key and batch["units"] + lot["units"] <= request["capacity"]:
                batch["ids"].append(lot["id"])
                batch["units"] += lot["units"]
                break
        else:
            batches.append(dict(key=key, units=lot["units"], ids=[lot["id"]]))
    return [b["ids"] for b in batches]
