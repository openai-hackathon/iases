# Public behavior contract

events contains receipt or reversal records with nonnegative integer quantity. Sum receipts positively and reversals negatively. Return the signed net quantity, including negative totals.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
