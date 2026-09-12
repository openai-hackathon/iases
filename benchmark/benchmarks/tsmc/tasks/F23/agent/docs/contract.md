# Public behavior contract

jobs is a DAG in arbitrary order, with unique id, one resource, nonnegative duration and depends ids. Repeatedly choose the lexicographically smallest job whose dependencies have been scheduled. Start at max(resource availability, dependency finish times, release time). Resources start free at zero. Return jobs sorted by id with [start,end]. This is deterministic list scheduling, not makespan optimization. Reject cyclic graphs with ValueError.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
