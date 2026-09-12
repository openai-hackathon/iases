# A04 Author notes

## Root cause
The event-time watermark is incorrectly used as a deduplication key/cursor, discarding equal-time and late events that have not been processed.

## Reference fix
Use ingestion offsets to control replay and event_id for semantic deduplication; the event_time watermark is diagnostic only.

The reference implementation is not the only allowed solution. Grade public-contract behavior with tests; every hidden test corresponds to the public contract.

## Known scope
This is a small synthetic fixture. Codex/Qwen repair difficulty, tool-call counts and scheduling gains have not been measured.
