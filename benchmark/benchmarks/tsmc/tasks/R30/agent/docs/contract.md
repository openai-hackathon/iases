# Public behavior contract

artifacts is an unordered catalog with unique (id,revision) pairs. Each entry has a string id, positive integer revision, UTF-8 content, declared lowercase sha256, revoked boolean, and requires containing exact [id,revision] references. install(roots,crash=false) resolves the complete reachable closure of exact roots, never the latest revision. Missing or revoked reachable entries, dependency cycles, two revisions of one id in the closure, or a content/digest mismatch anywhere in the closure return invalid and preserve the current package. Unreachable bad entries are ignored. Traverse roots sorted by (id,revision), recursively visit dependencies in that same order, emit each node once after its dependencies; duplicate roots/dependencies and diamond sharing are allowed. On success atomically replace all installed rows in a real SQLite transaction and return installed. An injected crash after deleting the previous rows but before inserting replacements returns crashed and must preserve the previous package across restart. Empty roots install an empty package. restart closes/reopens the same file and returns restarted. Return results and installed [id,revision,content] rows in dependency traversal order. Validation precedes the crash point. The graph may contain up to 40 revisions and arbitrary sharing, cycles and conflicting pins.Version 2 extends each root/dependency reference to either [id,exact_revision] or
[id,min_revision,max_revision], inclusive positive bounds. A closure chooses one
revision per reachable id satisfying ALL incoming constraints. Range choices may
introduce different transitive dependencies. Search all feasible closures; invalid,
revoked, corrupt or cyclic choices can be bypassed ONLY when another allowed
revision has a valid closure. Among valid closures maximize the revision vector
over all catalog ids sorted lexicographically, using 0 for absent ids. No unrelated
artifact may be included. Emit the chosen closure by the original sorted-root,
sorted-reference dependency-first traversal. Exact-pin behavior remains unchanged.

Maintain durable revision floors per artifact: every successful installation raises
each included artifact's floor to its installed revision. Never select a revision
below its floor, even after an empty installation, removal, failed install or restart.
Floors apply to dependencies as well as roots. Every successful publication,
including an empty one, increments a global generation initially 0.

prepare(id,roots,crash=false) resolves and verifies a closure against current floors
and durably records an immutable ticket containing its closure and current generation,
without changing installed data or floors. Return prepared, invalid, or crashed.
Reusing a ticket id with the same root LIST normalized by sorting and deduplication
returns prepared; different roots return conflict. Existing tickets are not rebased.
Two-element and three-element reference encodings remain distinct ticket identities.
A prepare crash rolls back ticket creation. Invalid resolution precedes crash.

commit(id,crash=false) returns missing if no ticket exists, installed if that ticket
already committed (with no further generation advance), or stale when its recorded
generation differs from the current one. Otherwise publish the recorded closure,
floors, generation and committed ticket status atomically. A crash rolls all four
back and leaves the ticket retryable. Generation checking must be in the same
transaction as publication. Direct install also advances generation and can stale
pending tickets. Existing status checks precede crash handling. Catalog contents
stay fixed for the request. At most 12 distinct ids and 40 catalog revisions.
Return the original results/installed shape. All state survives actual SQLite reopen.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
