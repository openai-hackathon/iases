# Public behavior contract

rows contains group/part/good records. The last row for a part is its authoritative group and boolean good status. Return sorted groups mapping to {good,total}, counting each unique part once. Groups with no current members are omitted; part identity is global.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
