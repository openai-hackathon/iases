# R03 Author notes

## Root cause
The checkpoint is committed separately first, advancing the recovery cursor beyond durable output.

## Reference fix
Write each output and checkpoint in one transaction, output first; both injection points precede commit. Roll back on failure and replay that event.

The reference implementation is not the only allowed solution. Grade public-contract behavior with tests; every hidden test corresponds to the public contract.

## Known scope
This is a small synthetic fixture. Codex/Qwen repair difficulty, tool-call counts and scheduling gains have not been measured.
