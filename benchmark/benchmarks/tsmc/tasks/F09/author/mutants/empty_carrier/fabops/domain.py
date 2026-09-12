def run(request):
    quantity, capacity = request["quantity"], request["capacity"]
    return max(1, (quantity + capacity - 1) // capacity)
