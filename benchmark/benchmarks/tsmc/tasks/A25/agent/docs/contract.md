# Public behavior contract

edges is a directed material lineage graph [parent,child], possibly cyclic or duplicated. Return sorted ids reachable from any seed through one or more edges, excluding the seed ids themselves. Unknown seeds produce no descendants. Traversal must terminate on cycles.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
