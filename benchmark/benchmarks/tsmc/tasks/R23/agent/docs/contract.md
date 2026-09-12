# Public behavior contract

Each response has nextSequence, the sequence to request next, and observations with sequence numbers. Return response nextSequence values unchanged, including empty filtered responses. The header already identifies the first unread sequence; it is not the last observation.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
