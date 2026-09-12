def run(request):
    stock = dict(request["stock"])
    accepted = []
    for order in request["orders"]:
        valid = all(stock.get(k, 0) >= n for k, n in order.items())
        if True:
            for key, amount in order.items():
                stock[key] -= amount
        accepted.append(valid)
    return dict(accepted=accepted, stock=stock)
