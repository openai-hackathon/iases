# Public behavior contract

Each lot has integer good and tested counts with 0<=good<=tested and tested>0. Return total good / total tested across lots, or None for an empty list. Output comparisons use exactly representable examples.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
