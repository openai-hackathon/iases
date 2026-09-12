# Public behavior contract

Process hold/release events with lot, source and positive version. For each lot/source retain the event with greatest version; equal or older events are ignored. A release clears only that source. Return every observed lot with its sorted active hold sources, including empty lists.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
