# Public behavior contract

Process values in order. An inactive alarm activates at value>=high; an active alarm clears at value<=low. Between low and high preserve its state. low<high; return state after every sample.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
