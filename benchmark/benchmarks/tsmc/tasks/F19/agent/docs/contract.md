# Public behavior contract

Plan a bounded nonpreemptive dispatch and atomically publish its reservations.
There are at most six unique lots, three tools, and an integer horizon 1..8.
Each lot has id, nonnegative priority, reticle, nonnegative costs by eligible
tool, positive integer durations for those same tools, integer release>=0,
deadline<=horizon, optional units>=1 (default 1), cooldown>=0 (default 0),
and after (default []), listing existing predecessor lot ids in an acyclic graph.
Release may exceed the latest feasible start. Stock maps reticles to nonnegative
concurrent capacity; absent reticles have zero capacity. Tools is a unique list.
Maintenance maps tools to arbitrary, possibly overlapping half-open integer intervals.

A selected lot occupies one eligible tool during [start,end), end=start+duration.
Start is an integer >=release, end<=deadline and horizon. It cannot overlap
maintenance or another reservation on the same tool. It reserves units of its
reticle during [start,end+cooldown); reticles are reusable after this interval,
not consumed permanently. Concurrent demand cannot exceed stock. A selected
lot requires ALL its predecessors selected and finished by its start. Cooldown
delays reuse of the reticle, not precedence completion or tool reuse.

Optimize globally: maximize selected count, then priority sum, then minimize
total tool cost, then sum of completion times, then the lexicographic list of
[lot id,tool id,start,end] rows sorted by lot id. Deliberate idle time and
non-earliest placements may be necessary. Return the complete optimal plan.

Commit checks exact equality of observed and current revision objects, including
missing/extra keys. Mismatch takes precedence over crash and returns status=stale.
Otherwise atomically insert all reservations into a real SQLite file. crash=true
interrupts after insertion and before commit: status=crashed and no published
reservations, including after reopen. Success returns status=committed. Empty
plans follow the same commit rules. Return plan,status,reservations; the latter
is the entire published plan on success and [] otherwise. Do not mutate inputs.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
