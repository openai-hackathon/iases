# Public behavior contract

rows contains unique id records with time and value. Sort by (time,id). cursor is None or a [time,id] exclusive lower bound. Return up to limit rows, with next_cursor equal to the last returned [time,id], or the input cursor when no rows return. limit>=1. Do not mutate input rows.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
