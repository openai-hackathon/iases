def run(request):
    received = {}
    for receipt in request["receipts"]:
        key = receipt["line"]
        received[key] = received.get(key, 0) + receipt["quantity"]
    billed = dict.fromkeys(request["orders"], 0)
    accepted = []
    for invoice in request["invoices"]:
        key, quantity = invoice["line"], invoice["quantity"]
        valid = key in billed and quantity <= min(request["orders"][key], received.get(key, 0))
        if valid:
            billed[key] += quantity
        accepted.append(valid)
    return dict(accepted=accepted, billed=billed)
