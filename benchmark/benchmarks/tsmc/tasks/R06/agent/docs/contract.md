# Public behavior contract

Return min(cap, base*2**attempt+jitter). attempt is an integer in [0,20]; base>0, cap>=base, jitter>=0. Jitter is supplied explicitly so tests do not depend on random number generators.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
