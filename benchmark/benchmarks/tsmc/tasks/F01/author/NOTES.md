# F01 Author notes

## Root cause
The eligibility conjunction omits quality_hold; the other restrictions already exist.

## Reference fix
Add the not-held requirement to the same conjunction; preserve eligible positives and fail-closed behavior for unknown IDs.

The reference implementation is not the only allowed solution. Grade public-contract behavior with tests; every hidden test corresponds to the public contract.

## Known scope
This is a small synthetic fixture. Codex/Qwen repair difficulty, tool-call counts and scheduling gains have not been measured.
