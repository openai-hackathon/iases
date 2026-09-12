# A01 Author notes

## Root cause
covered_seconds sums interval lengths instead of their union; the loader already clips windows and handles timezones correctly.

## Reference fix
Sort and merge overlapping/adjacent intervals, then sum. Tests use a set of covered integer seconds as an independent algorithmic oracle.

The reference implementation is not the only allowed solution. Grade public-contract behavior with tests; every hidden test corresponds to the public contract.

## Known scope
This is a small synthetic fixture. Codex/Qwen repair difficulty, tool-call counts and scheduling gains have not been measured.
