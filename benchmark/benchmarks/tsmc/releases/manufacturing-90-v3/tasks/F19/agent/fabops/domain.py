from .planner import plan
from .store import commit_plan
def run(request):
    pairs = plan(request["lots"], request["tools"], request["stock"])
    accepted, stock = commit_plan(pairs, request["lots"], request["stock"],
                                  request["observed"], request["current"])
    return dict(plan=pairs, committed=accepted, stock=stock)
