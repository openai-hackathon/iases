# Public data dictionary

All data is synthetic. These rules and `contract.md` together define the public requirements.

| Field | Type | Example | Meaning |
|---|---|---|---|
| limit | positive integer excluding bool | 2 | Maximum concurrent local asyncio slot ownership |
| job | zero-arg callable returning awaitable | async function | Return results and propagate exceptions unchanged |
| active/free_slots/peak | integer counters | 0/2/1 | Count successful acquires; cancelled waiters must not release extra slots |
| jobs[].outcome | ok / error / cancel | error | Fixed CLI scenarios; tests additionally use actual Task.cancel |
| jobs[].values | number list | [1,2,3] | Successful jobs compute the sum; no sleep-based duration simulation |

## File roles
`data/request.json` is the complete and sole CLI input; `data/expected.json` is its public expected result. CSV/JSONL source tables support inspection and custom analysis and are not implicitly loaded by the program.
`data/load_128.json` is an input-size variant with a fixed seed, no new defects and no hidden answers. Run it with the same CLI.

## Invalid inputs and scope limits
Only invalid-input behavior explicitly specified by the contract is graded. Do not infer real equipment safety or production rules from synthetic data.
