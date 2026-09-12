# Public behavior contract

events contains call records with now and success. A closed breaker opens after threshold consecutive failures. While open, reject calls until now>=opened_at+cooldown. The first eligible call is a probe: success closes and resets failures, failure reopens at now. Return accepted flags, state and failures. Times are nondecreasing, threshold>=1 and cooldown>0.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
