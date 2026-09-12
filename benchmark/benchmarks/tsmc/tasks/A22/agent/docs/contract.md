# Public behavior contract

measurements contains value and unit, one of Pa, kPa or bar. Return values in Pa using 1 kPa=1000 Pa and 1 bar=100000 Pa. Preserve zero and negative gauge pressures and input order.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
