# Public data dictionary

All data is synthetic. These rules and `contract.md` together define the public requirements.

| Field | Type | Example | Meaning |
|---|---|---|---|
| steps[].lot_id/machine_id | string | L1/E1 | Multiple steps per lot; association requires the same machine |
| steps[].enter/exit | ISO8601 offset | 00:00-00:30 | Half-open interval; reversal raises ValueError |
| events[].event_id | string | evt-1 | Unique event or identical replay |
| events[].start/end | ISO8601 offset | 00:10-00:20 | Zero duration and touching endpoints do not contribute |
| output event_ids | unique sorted strings | [evt-1,evt-2] | One row per lot retaining every matching piece of evidence |

## File roles
`data/request.json` is the complete and sole CLI input; `data/expected.json` is its public expected result. CSV/JSONL source tables support inspection and custom analysis and are not implicitly loaded by the program.
`data/load_128.json` is an input-size variant with a fixed seed, no new defects and no hidden answers. Run it with the same CLI.

## Invalid inputs and scope limits
Only invalid-input behavior explicitly specified by the contract is graded. Do not infer real equipment safety or production rules from synthetic data.
