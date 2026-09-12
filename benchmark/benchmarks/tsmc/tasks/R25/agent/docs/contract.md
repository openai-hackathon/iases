# Public behavior contract

Initial SQLite table measurements has one INTEGER value column populated from values. Migration atomically adds unit TEXT and fills it with 'Pa'. fail injects an exception after ALTER TABLE; rollback must restore the original schema and values. If retry is true, retry once without failure. Return columns and rows in insertion order. The migrate(connection, fail) function must use an actual SQLite transaction; no network or filesystem persistence is needed for this task.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
