# Public behavior contract

Within integer horizon [start,end), assign each blocked minute to exactly one cause. intervals contains cause/start/end records with half-open bounds. priority lists all causes from highest to lowest. Return durations for every listed cause, including zero. Clip intervals to the horizon.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
