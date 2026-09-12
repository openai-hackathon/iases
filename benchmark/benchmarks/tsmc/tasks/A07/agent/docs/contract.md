# Public behavior contract

values contains finite numbers or None for unavailable measurements. Average only numeric measurements, including zero and negative values; return None if none are available.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
