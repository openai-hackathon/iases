# Public behavior contract

stock and balance are nonnegative integers. orders contain quantity>0, price>=0 and failure ('none', 'charge', or 'after_charge'). Reject insufficient stock or balance without side effects. Otherwise reserve quantity, charge price, then complete. Injected failure must compensate all completed steps exactly once. Return accepted flags, stock and balance after all orders.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
