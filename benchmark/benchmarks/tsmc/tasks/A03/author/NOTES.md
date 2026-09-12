# A03 Author notes

## Root cause
Each join match is emitted separately without returning to lot grain or deduplicating the evidence set.

## Reference fix
Retain half-open interval intersection semantics, aggregate all matches into lot->event_id sets, then sort deterministically.

The reference implementation is not the only allowed solution. Grade public-contract behavior with tests; every hidden test corresponds to the public contract.

## Known scope
This is a small synthetic fixture. Codex/Qwen repair difficulty, tool-call counts and scheduling gains have not been measured.
