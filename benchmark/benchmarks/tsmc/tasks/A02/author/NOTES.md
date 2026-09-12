# A02 Author notes

## Root cause
Valid rows are aggregated directly by lot, ignoring wafer grain and retest selection.

## Reference fix
First select the valid record with maximum (UTC timestamp,test_id) per (lot,wafer), then aggregate by lot.

The reference implementation is not the only allowed solution. Grade public-contract behavior with tests; every hidden test corresponds to the public contract.

## Known scope
This is a small synthetic fixture. Codex/Qwen repair difficulty, tool-call counts and scheduling gains have not been measured.
