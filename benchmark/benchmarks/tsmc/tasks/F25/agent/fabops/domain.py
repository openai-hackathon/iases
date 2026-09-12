from .alignment import search

def run(request):
    cost, path = search(request)
    return dict(accepted=cost is not None, cost=cost,
                alignment=[dict(kind=k, event=e or None, transition=t or None)
                           for k, e, t in path],
                log_moves=sum(k == "log" for k, _, _ in path),
                model_moves=sum(k == "model" for k, _, _ in path),
                synchronous_moves=sum(k == "sync" for k, _, _ in path))
