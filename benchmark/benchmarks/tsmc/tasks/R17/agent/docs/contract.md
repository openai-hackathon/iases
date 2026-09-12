# Public behavior contract

capacity>=1 and rate>0 are integers. Initially the bucket is full at time zero. For nondecreasing integer request times, refill min(capacity,tokens+(now-last)*rate), then consume one if available. times use milliseconds and rate uses tokens/second. Preserve fractional credit. Return accepted and remaining milli-tokens as integers (1000 per token).

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
