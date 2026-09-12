# Public behavior contract

Implement a durable ordered publication service using the existing SQLite file. Two
consumers, mes and quality, begin with next=1,total=0,trail=[],buffered=[]. Source begins
next_sequence=1,total=0,epoch=0,compacted=0. append(id,delta,crash=false) assigns the next
global sequence, advances it, adds integer delta to source total, remembers the immutable
id/delta/sequence and records an outbox payload in ONE transaction. An identical id/delta
retry returns its original sequence even after compaction. A changed delta under an old id
returns conflict. A crash before the outbox write returns crashed and preserves ALL source
state. Deltas are integers between -1000 and 1000. Return the assigned sequence for successful append/retry.

acquire(owner,now,ttl) returns null while a lease is unexpired; otherwise grant a strictly
increasing durable positive token, with expires=now+ttl. ttl is positive; command times are
nonnegative, nondecreasing integers at most 1000000, and ttl is at most 10000. retire(owner,token,now) deletes an active matching lease and returns retired;
otherwise fenced. Retiring never resets the durable epoch. deliver and compact require
matching owner AND token and now<expires, otherwise return fenced without any effect.

deliver(seq,consumer,owner,token,now,crash=none) returns missing for an unavailable outbox
sequence, or acked if already locally acknowledged. Otherwise before_sink crash returns
crashed with no changes. The sink transaction buffers the event durably and drains ONLY
its contiguous sequence prefix: for each newly applied event add delta, append its id to
trail, advance next and remove its buffer row. A duplicate sequence below next does not
apply again. Out-of-order events remain buffered across restart; no gap may be skipped.
An after_sink crash commits this consumer state but leaves the local ack absent, returning
crashed. Normal delivery then commits a separate (sequence,consumer) ack and returns acked,
including for buffered events. Retry must neither lose the sink effect nor duplicate it.

compact(owner,token,now,crash=false) reclaims only the largest contiguous prefix beyond
compacted for which BOTH consumers have applied every event AND BOTH local acks exist.
Atomically delete outbox/ack rows through that cut and advance compacted, returning the
cut. Never discard durable command identities, source next_sequence, lease epoch, consumer
totals/trails or gap buffers. A compaction crash after its SQL deletes but before commit
returns crashed and preserves the former durable state. A valid call with no eligible
prefix returns the unchanged cut. restart closes/reopens the same file and returns restarted.

Return per-command results; source next_sequence,total,epoch,compacted; active lease as
[owner,token,expires] or null; consumers with next,total,trail and sorted buffered sequences;
sorted retained outbox sequences; sorted [sequence,consumer] acks; and commands count.
Total/trail/next are observable durable consumer state, not recomputed from retained outbox
rows. Every sink application and local ack are separate real SQLite commits; actual disk
reopen and rollback matter. There are at most 50 commands, 12 appended ids, and two consumers.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
