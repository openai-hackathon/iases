# Public behavior contract

Process lots in input order with first-fit packing. A batch can contain only equal product, recipe and reticle values, with summed units<=capacity. Each lot has 1..capacity units and a unique id. Return batches as lists of lot ids, preserving batch creation and insertion order.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
