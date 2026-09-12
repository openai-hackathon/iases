# Public behavior contract

samples contains [sequence,count] readings with unique positive sequence and nonnegative count. Sort by sequence. The first reading is the baseline, contributing zero. Subsequent increases contribute the difference; a decrease denotes reset to zero and contributes the new count. Return total.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
