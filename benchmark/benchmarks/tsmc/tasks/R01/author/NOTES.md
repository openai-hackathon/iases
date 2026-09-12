# R01 Author notes

## Root cause
Every submit creates a work_order and overwrites the operation receipt without checking an already-executed key in the same transaction.

## Reference fix
Use BEGIN IMMEDIATE to protect lookup and creation. Compare canonical payload for an existing key and return the saved result; inject response loss only after commit.

The reference implementation is not the only allowed solution. Grade public-contract behavior with tests; every hidden test corresponds to the public contract.

## Known scope
This is a small synthetic fixture. Codex/Qwen repair difficulty, tool-call counts and scheduling gains have not been measured.
