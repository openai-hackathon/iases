# Public behavior contract

route is an ordered list of step names, with repeats allowed. completed is the number of completed occurrences, between zero and len(route). Return the next step or None when complete.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
