# Public behavior contract

Return the minimum setup cost from start to end in a directed graph of [from,to,cost] edges. Costs are nonnegative integers; nodes are strings. Return None if unreachable and zero for same node.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
