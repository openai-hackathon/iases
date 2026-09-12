# Public behavior contract

Return the minimum whole carriers needed for quantity units with positive integer capacity. quantity is a nonnegative integer; an empty order needs zero carriers.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
