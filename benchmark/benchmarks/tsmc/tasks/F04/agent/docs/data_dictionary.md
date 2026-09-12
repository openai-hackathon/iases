# Public data dictionary

All data is synthetic. These rules and `contract.md` together define the public requirements.

| Field | Type | Example | Meaning |
|---|---|---|---|
| sensors[id].kind | enum | pressure | pressure or temperature |
| sensors[id].high | finite number | 2000.0 | Threshold in Pa or C; only strictly greater values alarm |
| readings[].value | number / numeric string / null | 3 | None is MISSING first; bool and non-finite values are INVALID |
| readings[].unit | string | kPa | Pressure: Pa/kPa/MPa/mbar; temperature: C/K/F |
| status/value_base | enum/number / null | ALARM/3000 | Unknown sensors raise ValueError; other invalid measurements are INVALID |

## File roles
`data/request.json` is the complete and sole CLI input; `data/expected.json` is its public expected result. CSV/JSONL source tables support inspection and custom analysis and are not implicitly loaded by the program.
`data/load_128.json` is an input-size variant with a fixed seed, no new defects and no hidden answers. Run it with the same CLI.

## Invalid inputs and scope limits
Only invalid-input behavior explicitly specified by the contract is graded. Do not infer real equipment safety or production rules from synthetic data.
