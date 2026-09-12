# Public behavior contract

The SingleFlight.get(key, loader) async API shares one running loader task per key. Cancelling a waiter must not cancel the shared loader or other waiters. Failed or completed tasks must be removed before the next independent request. run performs deterministic rounds: keys lists concurrent callers, cancel lists caller indices. Return per-round results ('cancelled' for cancelled waiters, otherwise the key) and total loader calls by key. Keys are strings. No wall-clock sleeps.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
