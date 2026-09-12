# F04 Author notes

## Root cause
normalize only casts the raw number to float without converting to the threshold dictionary's base unit.

## Reference fix
Convert linearly by dimension and unit before finite-value and threshold checks; preserve explicit missing/invalid classifications.

The reference implementation is not the only allowed solution. Grade public-contract behavior with tests; every hidden test corresponds to the public contract.

## Known scope
This is a small synthetic fixture. Codex/Qwen repair difficulty, tool-call counts and scheduling gains have not been measured.
