# Public behavior contract

ids is an ordered unique list of request ids. responses has unique id/value pairs in arbitrary order, possibly missing requests or containing unrelated ids. Return values in request order, using None for missing responses. Preserve zero, false and null values.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
