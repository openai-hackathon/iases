# F02 Author notes

## Root cause
Cache reads use only the three-field qualification key and stop checking versions after the first hit.

## Reference fix
Store (version, result) in cache entries and validate against the latest registry version on every query, or use equivalent correct invalidation. Retain existing monotonic-version and conflict rules.

The reference implementation is not the only allowed solution. Grade public-contract behavior with tests; every hidden test corresponds to the public contract.

## Known scope
This is a small synthetic fixture. Codex/Qwen repair difficulty, tool-call counts and scheduling gains have not been measured.
