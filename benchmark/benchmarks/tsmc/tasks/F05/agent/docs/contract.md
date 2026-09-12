# Public behavior contract

A material is usable strictly before its expires_at minute. Return one boolean per lot. now and expires_at are integer UTC minutes; zero and negative historical timestamps are valid.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
