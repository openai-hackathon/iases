# Public data dictionary

All data is synthetic. These rules and `contract.md` together define the public requirements.

| Field | Type | Example | Meaning |
|---|---|---|---|
| machine_id | string | M-01 | Analyze only this machine; exclude others before parsing |
| window_start/window_end | ISO8601 offset | 2026-01-15T00:00:00Z | Half-open window with end>start |
| events[].start/end | ISO8601 / null | 00:10-00:25 | end=null means still open; reversed non-null intervals are invalid |
| event_id | string | a | Not an aggregation deduplication key; use interval union |
| downtime_fraction | float | 0.416666... | Union downtime seconds / observation-window seconds; not an industry OEE definition |

## File roles
`data/request.json` is the complete and sole CLI input; `data/expected.json` is its public expected result. CSV/JSONL source tables support inspection and custom analysis and are not implicitly loaded by the program.
`data/load_128.json` is an input-size variant with a fixed seed, no new defects and no hidden answers. Run it with the same CLI.

## Invalid inputs and scope limits
Only invalid-input behavior explicitly specified by the contract is graded. Do not infer real equipment safety or production rules from synthetic data.
