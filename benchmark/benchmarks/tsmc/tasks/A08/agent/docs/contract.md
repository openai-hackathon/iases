# Public behavior contract

edges is a strictly increasing numeric list of at least two entries. All bins are [left,right), except the final bin includes the final edge. Ignore values outside the edges; return bin counts.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
