# Public behavior contract

changes contains effective/value records; last arrival wins for an equal effective time. Rebuild nonoverlapping validity intervals sorted by effective time: [start,next_start), final end=None. Return start/end/value records. Late arrivals split the preceding interval; adjacent equal values remain separate revisions.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
