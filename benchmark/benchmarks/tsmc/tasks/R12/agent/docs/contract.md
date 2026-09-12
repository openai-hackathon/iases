# Public behavior contract

messages is an ordered list of unique id/valid records. For each message, valid is a JSON boolean. Invalid messages fail exactly max_attempts times then enter dead_letter. Valid messages process once. Return processed ids, dead_letter ids and attempts by id. max_attempts is positive; continue past poison.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
