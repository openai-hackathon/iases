# R02 Author notes

## Root cause
Capacity is observed before the write transaction. Both calls read old usage, then serialized inserts rely on that stale observation.

## Reference fix
After waiting at the synchronization hook, acquire a SQLite write transaction before reading usage, validating and inserting; roll back failures.

The reference implementation is not the only allowed solution. Grade public-contract behavior with tests; every hidden test corresponds to the public contract.

## Known scope
This is a small synthetic fixture. Codex/Qwen repair difficulty, tool-call counts and scheduling gains have not been measured.
