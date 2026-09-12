# Public behavior contract

samples is an unordered list of [second,watt] with unique integer seconds. Integrate the piecewise linear signal between the earliest and latest sample using trapezoids. Return joules; fewer than two samples return zero. Values are finite and nonnegative; do not extrapolate.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
