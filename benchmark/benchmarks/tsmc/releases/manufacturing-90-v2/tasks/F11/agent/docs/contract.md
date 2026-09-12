# Public behavior contract

Return available integer minutes in [start,end) after subtracting the union of maintenance intervals. Intervals are [left,right), may overlap, repeat or lie outside the horizon; left<=right.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
