# Public behavior contract

Manage atomic multi-resource leases and fenced versioned outputs in a real SQLite
file. resources lists 1..4 unique names; initially epochs are 0, no leases exist,
outputs are [revision=0,value=None]. Resource names in commands always exist.
Times are nondecreasing integers, ttl>0, owners and values are strings. Sets in
commands are nonempty; acquire.resources may repeat names and means their set.

acquire(owner,resources,now,ttl): if ANY requested resource has a lease with
now<expires, return None with no changes, even to otherwise available resources.
Otherwise atomically increment EACH resource's independently durable epoch,
replace all requested leases with [owner,token=epoch,expires=now+ttl], and return
the resource->token mapping. Expired rows can be replaced. Successful acquisition
increments every requested epoch, including reacquisition by the same owner;
release or restart never resets epochs. Unrequested resources are unchanged.

renew(owner,tokens,now,ttl) and release(owner,tokens,now) require every resource
to have exactly that owner/token and now<expires. Return False with no effects
if any check fails. Renewal extends EACH expiry to max(old_expiry,now+ttl)
without changing tokens; release removes exactly those active leases, preserving
epochs and outputs. Success returns True. Subsets of an earlier grant are allowed.

write(owner,tokens,expected,updates,now): tokens, expected and updates must have
exactly the same resource keys. Require the full live ownership check and all
expected revisions equal their current output revisions. If any condition fails,
return False and change nothing. Otherwise write every value, increment every
output revision by one and return True. Lease validation, revision reads and all
writes share one immediate transaction; no partial scope or partial write is legal.

Any modifying command may set crash=true: if validation fails, return its normal
failure first; otherwise interrupt after SQL changes and before commit, rollback
EVERYTHING including epoch allocations, and return 'crashed'. restart closes and
reopens the same file and returns 'restarted'. read uses a separate connection and
returns a durable snapshot. Return results plus final epochs, leases and outputs;
snapshots use those same three maps. Expired leases remain visible until explicitly
replaced or released. At most 50 commands. Do not mutate requests or simulate disk
persistence solely in process memory.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
