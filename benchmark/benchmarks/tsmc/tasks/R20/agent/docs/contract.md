# Public behavior contract

For every value in timeouts, return whether it is an integer from 1 through 300 inclusive. JSON booleans, strings, null, fractional and integral floats are invalid; Python bool being an int subclass must not admit it.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
