# Public behavior contract

entries contains tenant/key/value records; later records replace earlier values for exactly the same pair. queries contains tenant/key records. Return values or None for missing pairs. Tenant and key strings are case sensitive and may contain colons.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
