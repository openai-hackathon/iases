def run(request):
    stock = dict(request["stock"])
    accepted = []
    for operation in request["operations"]:
        inputs, outputs = operation["inputs"], operation["outputs"]
        valid = (bool(inputs) and bool(outputs) and all(k in stock for k in inputs)
                 and all(k not in stock and n > 0 for k, n in outputs.items()))
        if valid:
            valid = sum(stock[k] for k in inputs) >= sum(outputs.values())
        if valid:
            for key in inputs:
                del stock[key]
            stock.update(outputs)
        accepted.append(valid)
    return dict(accepted=accepted, stock=stock)
