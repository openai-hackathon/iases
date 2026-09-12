# Public behavior contract

capacity is nonnegative. Process put(key,weight) and get(key) operations. Positive integer weights count toward capacity. Reject oversized puts without changing anything. Other puts replace and become most recent, evicting oldest until within capacity. Successful gets promote; missing gets do nothing. Return keys oldest-to-newest and total weight.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
