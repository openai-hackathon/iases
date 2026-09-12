# Public behavior contract

commands has key, method, target, payload and result. First use of an idempotency key stores its fingerprint and result. Later identical commands return the stored result; different commands return 'conflict' and do not update storage. Fingerprint includes case-sensitive method, target and JSON payload, ignoring object key order recursively but preserving list order and numeric encoding. Results are strings other than 'conflict'. Return the response list.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
