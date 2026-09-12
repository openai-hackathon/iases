# Public behavior contract

Select the numerically greatest dotted revision string. All revisions have three nonnegative integer components without leading zeros. Empty input returns None. Preserve the original string.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
