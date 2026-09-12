# Public behavior contract

labels contains -1 for pass and +1 for fail. Return failure booleans in the same order. Only these two integer labels are valid; label magnitude is not a probability.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
