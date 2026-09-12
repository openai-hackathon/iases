# Public behavior contract

Each qualification has start/end ISO8601 timestamps with explicit offsets and an id. Return sorted ids valid at the supplied offset-aware at timestamp using start<=at<end in absolute time.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
