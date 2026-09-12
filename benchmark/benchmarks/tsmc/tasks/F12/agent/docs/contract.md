# Public behavior contract

Rules match product and machine exactly or with '*'. Select the matching rule with most exact fields; ties use the greatest integer revision, then lexicographically smallest id. Return id or None.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
