# Public behavior contract

Reconstruct a firing witness for one production trace in a bounded weighted Petri net.
capacities maps up to six named places to positive integer limits at most three.
initial and final map places to nonnegative token counts within those limits; omitted
places mean zero. Each of at most ten transitions has a unique string id, label (a
string activity or null for an unobserved routing transition), and consume/produce
mappings with positive integer arc weights. Every mentioned place has a capacity.
A firing is allowed only when all input multiplicities are available and the marking
AFTER atomic consumption and production respects every capacity. Self loops consume
before producing. Silent cycles, parallel branches, repeated labels and repeated
activity occurrences are valid. trace contains at most eight observed activity labels.

Find a sequence whose non-null labels equal trace exactly and whose complete final
marking equals final, including zero and leftover places. Silent firings can occur
before, between or after observations. Among all witnesses minimize the number of
silent firings, then lexicographically minimize the full sequence of transition ids.
Return accepted=true, witness as that sequence, silent as its number of silent firings,
and marking containing every place. If no witness exists, return accepted=false,
witness=[], silent=null and the original marking with missing places filled by zero.
Rejected branches must not consume tokens from other branches or the request. Search
must terminate for silent cycles; tracking only activity position cannot distinguish
parallel markings. All input lists may arrive in arbitrary order except trace.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
