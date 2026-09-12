# Public behavior contract

capacity is positive. Process enqueue(id,weight), cancel(id) for waiting ids, and release(id) for active ids. Weights are 1..capacity, ids unique across enqueues. After every operation, admit as many head waiters as fit; never bypass a heavier head. Unknown cancel/release is a no-op. Return admission history, sorted active ids and pending ids in FIFO order.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
