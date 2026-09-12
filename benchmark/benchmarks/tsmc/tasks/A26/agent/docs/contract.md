# Public behavior contract

records contains key/version/value/deleted records. version is a positive integer; versions are unique per key. Keep the greatest version for each key, including tombstones. Return only live key/value pairs sorted by key. Partition input order must not affect the result.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
