# Public behavior contract

summaries contains count, mean and m2 (sum of squared deviations) for disjoint populations. Ignore zero-count groups. Return combined count, mean and population variance m2/count; an empty population returns mean=None, variance=None. Use the parallel variance formula with between-group mean correction. Test examples use exactly representable results.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
