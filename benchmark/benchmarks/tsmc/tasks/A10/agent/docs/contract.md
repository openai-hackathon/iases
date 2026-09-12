# Public behavior contract

values are decimal strings. Sum their exact decimal values, then round the total to two decimal places using ROUND_HALF_UP, returning a fixed two-place string. Empty input returns '0.00'.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
