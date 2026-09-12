# Public data dictionary

All data is synthetic. These rules and `contract.md` together define the public requirements.

| Field | Type | Example | Meaning |
|---|---|---|---|
| offset | integer >=0 | 0,1,2 | Single ingestion-partition cursor; complete delivered prefix across batches |
| event_id | string | e1 | Semantic deduplication key; replayed payload is identical |
| event_time | ISO8601 offset | 2026-01-15T00:01:00Z | Late and equal timestamps are allowed; not a discard threshold |
| machine_id/value | string / finite number | M/3 | Count and sum per machine |
| state.last_offset/watermark/seen/totals | JSON state | see expected.json | watermark is diagnostic; seen survives restart |

## File roles
`data/request.json` is the complete and sole CLI input; `data/expected.json` is its public expected result. CSV/JSONL source tables support inspection and custom analysis and are not implicitly loaded by the program.
`data/load_128.json` is an input-size variant with a fixed seed, no new defects and no hidden answers. Run it with the same CLI.

## Invalid inputs and scope limits
Only invalid-input behavior explicitly specified by the contract is graded. Do not infer real equipment safety or production rules from synthetic data.
