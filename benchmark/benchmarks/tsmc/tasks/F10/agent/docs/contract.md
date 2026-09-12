# Public behavior contract

Return True only if every required interlock name is present with JSON boolean true. Missing, false and nonboolean observations are unsafe. An empty required list is satisfied.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
