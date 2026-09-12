# Public data dictionary

All data is synthetic. These rules and `contract.md` together define the public requirements.

| Field | Type | Example | Meaning |
|---|---|---|---|
| machine_id/product_id/step_id | string tuple | M/P/S | Complete qualification key; no field may be omitted |
| version | integer >=0 | 2 | Monotonic per key, not global |
| valid | boolean | false | Revocation and reapproval must take effect immediately |
| actions[].op | query / update | query | query emits a boolean; update emits no item |
| missing qualification | absence | no record | Query returns False; a later addition must invalidate negative cache entries |

## File roles
`data/request.json` is the complete and sole CLI input; `data/expected.json` is its public expected result. CSV/JSONL source tables support inspection and custom analysis and are not implicitly loaded by the program.
`data/load_128.json` is an input-size variant with a fixed seed, no new defects and no hidden answers. Run it with the same CLI.

## Invalid inputs and scope limits
Only invalid-input behavior explicitly specified by the contract is graded. Do not infer real equipment safety or production rules from synthetic data.
