def run(request):
    queue, active, admitted = [], {}, []
    for op in request["operations"]:
        if op["op"] == "enqueue":
            queue.append((op["id"], op["weight"]))
        elif op["op"] == "cancel":
            pass
        else:
            active.pop(op["id"], None)
        while queue and sum(active.values()) + queue[0][1] <= request["capacity"]:
            key, weight = queue.pop(0)
            active[key] = weight
            admitted.append(key)
    return dict(admitted=admitted, active=sorted(active), pending=[k for k, _ in queue])
