# Public behavior contract

records contains unique id/offset entries with offset>=0. consumers contains active boolean and ack, the last durably processed offset (>=-1). Delete records only when offset<=every active consumer's ack. With no active consumers retain everything. Return retained ids in input order.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
