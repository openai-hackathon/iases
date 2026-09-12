# Code structure
 CLI `python -m fabops --input data/request.json` → `fabops.service.run()` → `fabops.sensors`。
 `request.json` is the complete CLI input; `expected.json` is the expected output for that public input.
 Other data files are readable source tables; the CLI does not implicitly read them or expected.json.
 Each task is an independent snapshot; data and state are not shared with other tasks.
 All data is synthetic and contains no actual company or manufacturing process information.
