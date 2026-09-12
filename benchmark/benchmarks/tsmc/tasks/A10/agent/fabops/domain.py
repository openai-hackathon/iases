from decimal import Decimal, ROUND_HALF_UP
def run(request):
    values = [Decimal(value) for value in request["values"]]
    total = sum((v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) for v in values), Decimal(0))
    return format(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), ".2f")
