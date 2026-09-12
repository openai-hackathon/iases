# Public behavior contract

Return the nearest-rank quantile of finite numeric values: sort ascending, select one-based rank max(1,ceil(q*n)), for q in [0,1]. Empty input returns None. Preserve duplicates.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
