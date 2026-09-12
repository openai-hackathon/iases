# Public behavior contract

An entry expires when now>=created+ttl. ttl is nonnegative. Return None for expired entries, otherwise return the stored JSON value unchanged; all times use the same supplied monotonic clock.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
