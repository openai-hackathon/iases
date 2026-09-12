# Public data dictionary

All data is synthetic. These rules and `contract.md` together define the public requirements.

| Field | Type | Example | Meaning |
|---|---|---|---|
| lots[lot_id] | object | L1 | Keyed by lot_id; values contain status/quality_hold/product_id/step_id |
| quality_hold | boolean | true | Always blocks scheduling; a valid qualification cannot override it |
| status / machine.state | string | WAITING / AVAILABLE | Only this combination permits scheduling; reject all others |
| qualifications[] | object | machine/product/step/valid | At least one valid match across all three fields; no version competition |
| assignments[] | object | lot_id, machine_id | Evaluate each independently, preserving input order |

## File roles
`data/request.json` is the complete and sole CLI input; `data/expected.json` is its public expected result. CSV/JSONL source tables support inspection and custom analysis and are not implicitly loaded by the program.
`data/load_128.json` is an input-size variant with a fixed seed, no new defects and no hidden answers. Run it with the same CLI.

## Invalid inputs and scope limits
Only invalid-input behavior explicitly specified by the contract is graded. Do not infer real equipment safety or production rules from synthetic data.
