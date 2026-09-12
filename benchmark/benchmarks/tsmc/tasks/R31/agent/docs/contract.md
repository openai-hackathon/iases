# Public behavior contract

sources lists 1-4 unique source ids. Each starts in epoch 0 with next sequence 1 and watermark -1. page(source,epoch,events,through,watermark,crash=false) accepts an unordered batch of unique positive sequence numbers with nonnegative integer time and integer value. Retain out-of-order events across real SQLite checkpoint/restart, advance next only through the contiguous prefix starting at 1, and defer each (through,watermark) barrier until every sequence <=through is present. The effective watermark is the maximum activated barrier (initially -1). Event time is nondecreasing with sequence within an epoch; valid barriers guarantee all later-sequence events have time greater than that barrier's watermark. Advertisements may arrive before their events. An identical event retry is accepted. A conflicting duplicate sequence rejects the entire page with conflict and no effects. A lower epoch returns stale; a higher epoch resets the entire source, including watermark, buffered events and barriers, before accepting the page. Other sources are unaffected. snapshot(crash=false) is blocked if any source watermark is -1; otherwise publish cut=min(all source watermarks), the epoch vector, and each source's last contiguous event value at time<=cut (highest sequence breaks tied times; None if none). A blocked snapshot preserves the previously published snapshot. Accepted pages and published snapshots checkpoint states and published value atomically. crash interrupts that checkpoint after its SQL write but before commit, returns crashed and changes neither memory nor reopened disk state. restart closes/reopens the actual file and returns restarted. Return results, the last published snapshot (initially None), and frontiers mapping sources to [epoch,next,watermark]. Snapshot history remains valid until replaced, even if a source enters a new epoch.Version 2 adds causal dependencies. Each event may include depends, a list of
[source,epoch,positive sequence] references, default []. Sources are known, epochs
are nonnegative; a referenced event need not yet be delivered. Every included
source contributes a PREFIX, never a sparse set. A snapshot first computes the
original cut=min(watermarks), then each source's maximum contiguous sequence
with event.time<=cut. This is only an upper bound: find the componentwise greatest
prefix vector at or below it whose EVERY included event's dependencies are also
included in the referenced source's CURRENT epoch. If a dependency is unavailable,
drop that event and its entire source suffix. Such retreat may invalidate earlier
choices on other sources, requiring further retreat until all references hold.
Mutual dependencies are allowed when both events are included. A mismatched old
or future dependency epoch cannot be satisfied by a numerically larger sequence.

snapshot may specify required={source:[epoch,minimum_sequence]}, default {}.
These are lower bounds, not overrides of completeness or causality. If the greatest
closed vector cannot meet any requested current-epoch floor, snapshot returns
blocked and preserves the prior publication, even with crash=true. A zero prefix
contributes value=None. Otherwise publish each source's latest value within its
closed prefix; cut remains the common watermark-derived TIME UPPER BOUND, not a
promise to include all events through that time. Return the original output shape.
Page frontiers remain receipt/watermark progress and are not reduced by causal
pruning. A later dependency page can make previously pruned events eligible again.
Dependency fields participate in identical-retry comparison and persist across
checkpoint/restart. At most 64 distinct events per source epoch and 50 commands.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
