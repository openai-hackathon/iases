# Public data dictionary

All data is synthetic. These rules and `contract.md` together define the public requirements.

| Field | Type | Example | Meaning |
|---|---|---|---|
| events[].sequence | positive integer | 1,2,3 | Strictly increasing per call, gaps allowed; old sequences replay a complete source |
| event_id/payload | JSON | event-1,{value:10} | Replayed content at the same sequence is identical |
| fail_at | integer / None | 2 | Sequence at which to inject failure |
| crash_point | enum / null | after_checkpoint | after_output or after_checkpoint, both before the event commits |
| checkpoint/outputs | durable state | 3,[...] | Output and cursor are atomic per event; tests inject exceptions, not power loss |

## File roles
`data/request.json` is the complete and sole CLI input; `data/expected.json` is its public expected result. CSV/JSONL source tables support inspection and custom analysis and are not implicitly loaded by the program.
`data/load_128.json` is an input-size variant with a fixed seed, no new defects and no hidden answers. Run it with the same CLI.

## Invalid inputs and scope limits
Only invalid-input behavior explicitly specified by the contract is graded. Do not infer real equipment safety or production rules from synthetic data.
