# Public behavior contract

For each integer minute in [0,1440), return whether it belongs to [start,end). If start>end the shift crosses midnight. Equal endpoints describe an empty shift. No timezone conversion is requested.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
