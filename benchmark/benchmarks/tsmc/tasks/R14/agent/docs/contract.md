# Public behavior contract

The initial lease has owner and expires. Each renewal supplies owner, now and ttl>0. Accept only the current owner while now<expires; set expires=now+ttl on acceptance. Return accepted flags and the final lease. Renewal times are nondecreasing and use a supplied monotonic clock.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
