# Public behavior contract

A real SQLite file holds isolated named uploads. begin(id,manifest) binds that id to an immutable manifest of {index,rows,sha256} chunk descriptors; indexes must be exactly 0..n-1 with no duplicates but input ordering is arbitrary. rows is a nonnegative count. sha256 is the lowercase SHA-256 of canonical UTF-8 chunk JSON: sorted object keys, compact separators, ensure_ascii=false; list order matters. begin returns started, resumed for an identical normalized manifest while open, committed for an identical completed manifest, conflict for a changed manifest, or invalid for invalid indexes. chunk(id,index,rows) stages a list of {key:string,value:integer} rows only if index, count and digest match its bound descriptor. Return missing for unknown upload, closed for completed upload, invalid for verification failure, duplicate for an identical staged retry, conflict for different staged content, otherwise staged. No staged row is query-visible before finish. finish(id,crash=false) returns missing, committed if already complete, incomplete if any chunk is absent, or invalid if any record key repeats across the whole batch. Reverify all chunks inside the publication transaction, then publish in chunk-index/row order and mark the upload committed atomically. An injected crash after writing published rows but before status update returns crashed, rolls back all publication effects and preserves staged chunks for retry. restart reopens the same database and returns restarted. Empty manifests commit empty batches. Different uploads may reuse record keys. Return results, published mapping only visible batch ids to row lists, all staged [id,index] pairs sorted by id/index, and states mapping every begun id to open or committed. Staged chunks are retained after commit for audit. Implement actual transactional persistence, not in-memory restart simulation.Version 2 adds shared revisioned dataset scopes and atomic group publication.
begin may specify scope (default upload id) and read_set={key:expected_revision}
(default {}). These fields are bound immutably together with the normalized chunk
manifest. Same manifest but different scope/read_set returns conflict even after
commit. Scopes are independent; staging never changes visible dataset records.

A chunk row now has key, expected (default 0), revision (default 1), and either
value (integer) or deleted=true for a tombstone. expected>=0 and revision>=1.
All fields participate in the canonical chunk digest. A published record version
starts at 0 for a never-seen key, and retains its last revision when tombstoned.
Recreating a deleted record therefore requires its tombstone revision as expected.

finish_group(ids,crash=false) normalizes a nonempty list of upload ids by sorting
and deduplicating; finish(id) means the singleton group. Check in order: any unknown
id gives missing; if every member is committed by this SAME normalized group return
committed without rewriting; any other committed member gives conflict; any missing
staged chunk gives incomplete; reverify every chunk; duplicate (scope,key) writes
anywhere in the group or revision<=expected gives invalid; any read_set mismatch
or row.expected mismatch against the CURRENT pre-transaction dataset gives stale.
Read sets are checked even for empty uploads and keys not being written. All
participants compare against the SAME pre-state, never another group's staged
updates or an earlier write in this group. Disjoint scopes may reuse record keys.

Only after all checks pass, atomically apply all records/tombstones, publish each
upload's immutable rows for audit, and mark EVERY upload committed by the group.
A crash after record/audit writes but before statuses rolls EVERYTHING back, retaining
staged chunks. Invalid/stale/incomplete/missing/conflict status precedes crash.
read(scope) uses a separate SQLite connection and returns values={key:[revision,value]}
for live records and versions={key:revision} INCLUDING tombstones. A later committed
update changes dataset reads but not an earlier upload's audit rows. restart must
preserve all versions, read sets, group receipts and unresolved staging on disk.
Final output remains results,published,staged,states. At most eight uploads, four
chunks each, twelve rows per chunk and 60 commands. Earlier unversioned uploads
retain their original behavior in their isolated default scopes.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
