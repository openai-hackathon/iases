def run(request):
    quantity, capacity = request["quantity"], request["capacity"]
    return (quantity + capacity - 1) // capacity
