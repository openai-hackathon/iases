# Public data dictionary

All data is synthetic. These rules and `contract.md` together define the public requirements.

| Field | Type | Example | Meaning |
|---|---|---|---|
| capacities[machine] | integer >=0 | 1 | Static capacity; initialize does not overwrite existing values |
| request_id | nonempty string | a | Identical replay succeeds; different content at the same ID conflicts |
| units | positive integer excluding bool | 1 | Capacity consumed on acceptance; never exceed capacity |
| hook | callable / None | barrier callback | Before the capacity critical section; do not wait while holding a lock; controls concurrency |
| fail_after_insert | boolean | true | Failure before commit must roll back completely |

## File roles
`data/request.json` is the complete and sole CLI input; `data/expected.json` is its public expected result. CSV/JSONL source tables support inspection and custom analysis and are not implicitly loaded by the program.
`data/load_128.json` is an input-size variant with a fixed seed, no new defects and no hidden answers. Run it with the same CLI.

## Invalid inputs and scope limits
Only invalid-input behavior explicitly specified by the contract is graded. Do not infer real equipment safety or production rules from synthetic data.
