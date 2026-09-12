# Public behavior contract

stock maps item names to nonnegative counts. orders is a sequence of item/count dictionaries, with positive requested counts. Accept an order only if every item is available; deduct all or none. Missing items have zero stock. Return accepted booleans and final stock, preserving original keys.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
