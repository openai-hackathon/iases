# Public behavior contract

orders maps line ids to ordered quantity. receipts contains line/quantity signed adjustments. invoices contains line/quantity with nonnegative quantities and is processed in order. Accept each invoice only if cumulative accepted quantity for that line stays <=ordered and <=net received. Unknown lines reject. Return accepted flags and billed quantities for every order line.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
