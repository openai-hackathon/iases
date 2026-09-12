# Public behavior contract

stock maps unique lot ids to positive integer units. Each operation lists distinct input ids and an outputs mapping. Accept only existing inputs, new output ids, positive output quantities, and equal total units. On acceptance consume inputs and add outputs atomically. Return accepted and stock.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
