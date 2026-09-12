# F03 Author notes

## Root cause
The reducer unconditionally accepts the last arrival, confusing arrival order with version order.

## Reference fix
Compare stale/equal/newer events against each machine's current sequence. Conflicting values at the current version must raise explicitly; preserve input immutability.

The reference implementation is not the only allowed solution. Grade public-contract behavior with tests; every hidden test corresponds to the public contract.

## Known scope
This is a small synthetic fixture. Codex/Qwen repair difficulty, tool-call counts and scheduling gains have not been measured.
