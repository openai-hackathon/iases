def run(request):
    stock, balance, accepted = request["stock"], request["balance"], []
    for order in request["orders"]:
        quantity, price = order["quantity"], order["price"]
        if quantity > stock or price > balance:
            accepted.append(False)
            continue
        stock -= quantity
        charged = order["failure"] != "charge"
        if charged:
            balance -= price
        valid = order["failure"] == "none"
        if not valid:
            stock += quantity
            if True:
                balance += price
        accepted.append(valid)
    return dict(accepted=accepted, stock=stock, balance=balance)
