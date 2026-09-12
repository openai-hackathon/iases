# Public data dictionary

All data is synthetic. These rules and `contract.md` together define the public requirements.

| Field | Type | Example | Meaning |
|---|---|---|---|
| lot_id/wafer_id | string tuple | L1/W1 | One denominator unit; wafer ID is unique only within a lot |
| tested_at | ISO8601 offset | 2026-01-15T08:00:00+08:00 | Compare in UTC |
| test_id | string | t2 | Lexicographic maximum breaks timestamp ties; unique ID or identical replay |
| valid/result | boolean + enum | true/PASS | Only valid=True participates; valid results must be PASS/FAIL |
| lot_ids | string list | [L1,empty] | Preserve deduplicated input order; empty lots have a null ratio |

## File roles
`data/request.json` is the complete and sole CLI input; `data/expected.json` is its public expected result. CSV/JSONL source tables support inspection and custom analysis and are not implicitly loaded by the program.
`data/load_128.json` is an input-size variant with a fixed seed, no new defects and no hidden answers. Run it with the same CLI.

## Invalid inputs and scope limits
Only invalid-input behavior explicitly specified by the contract is graded. Do not infer real equipment safety or production rules from synthetic data.
