# Public data dictionary

All data is synthetic. These rules and `contract.md` together define the public requirements.

| Field | Type | Example | Meaning |
|---|---|---|---|
| machine_id | string | E-02 | Independent reducer per machine |
| sequence | integer >=0 | 103 | Sole version key |
| new_state | enum | LOCKED | AVAILABLE/BUSY/MAINTENANCE/LOCKED |
| event_id/occurred_at/received_at | metadata | E-02-103 | Supplemental metadata, not version keys |
| initial[machine_id] | object | sequence,state | Valid initial state; defensively copy it |

## File roles
`data/request.json` is the complete and sole CLI input; `data/expected.json` is its public expected result. CSV/JSONL source tables support inspection and custom analysis and are not implicitly loaded by the program.
`data/load_128.json` is an input-size variant with a fixed seed, no new defects and no hidden answers. Run it with the same CLI.

## Invalid inputs and scope limits
Only invalid-input behavior explicitly specified by the contract is graded. Do not infer real equipment safety or production rules from synthetic data.
