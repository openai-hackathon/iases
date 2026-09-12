# Public behavior contract

times contains integer event times, potentially unordered and duplicated. Sort and deduplicate. Consecutive times belong to the same session when their gap<=gap; sessions return [first,last,count]. gap is nonnegative. A late event can connect two formerly separate sessions.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
