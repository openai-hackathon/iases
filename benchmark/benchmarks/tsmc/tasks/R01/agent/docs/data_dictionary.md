# Public data dictionary

All data is synthetic. These rules and `contract.md` together define the public requirements.

| Field | Type | Example | Meaning |
|---|---|---|---|
| key | nonempty string | incident-42 | Database-scoped idempotent operation ID |
| payload | exact object | machine_id,reason | Two nonempty strings; field order does not affect equality |
| lose_response | boolean | true | Inject ConnectionError after durable commit |
| work_order_id | opaque integer | 1 | Stable replay result ID; consecutive IDs are not required |
| operations table | durable receipt | key,payload,result | Written in the same transaction as the work order |

## File roles
`data/request.json` is the complete and sole CLI input; `data/expected.json` is its public expected result. CSV/JSONL source tables support inspection and custom analysis and are not implicitly loaded by the program.
`data/load_128.json` is an input-size variant with a fixed seed, no new defects and no hidden answers. Run it with the same CLI.

## Invalid inputs and scope limits
Only invalid-input behavior explicitly specified by the contract is graded. Do not infer real equipment safety or production rules from synthetic data.
