# Public behavior contract

cursor is the last contiguous acknowledged nonnegative sequence. acks contains positive sequence numbers, possibly unordered, repeated or older. Advance only over an uninterrupted run cursor+1, cursor+2, ...; acknowledgements beyond a gap must not advance the durable frontier.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
