def run(request):
    stock = dict(request["stock"])
    accepted = []
    for order in request["orders"]:
        valid = any(stock.get(k, 0) >= n for k, n in order.items())
        if valid:
            for key, amount in order.items():
                stock[key] -= amount
        accepted.append(valid)
    return dict(accepted=accepted, stock=stock)
