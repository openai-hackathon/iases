# Public behavior contract

attempts counts calls already made. Allow another attempt only when attempts<max_attempts AND elapsed<deadline. All four values are nonnegative finite numbers, and attempt counts are integers.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
