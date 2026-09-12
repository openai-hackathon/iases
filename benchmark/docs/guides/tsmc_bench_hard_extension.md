# Ten additional hard manufacturing repairs

This page records the archived v2 extension. The current v3 release revises only
seven selected development tasks, including A29, F25 and R29. See the
[development revision](tsmc_bench_development_revision.md) for their new contracts
and calibration; the remaining seven hard-extension tasks retain their v2 fixtures.

The `manufacturing-90-v2` release adds ten tasks to the frozen 80-task release.
All ten have **author-estimated hard difficulty**. Their empirical difficulty is
unmeasured: reference solutions and rejected incorrect repairs establish fixture
quality, not a model success rate. The request for ten hard tasks is a separate
cohort; it does not change the earlier 20/70/10 authoring policy.

## Source context

The [NIST SMS test bed](https://www.nist.gov/laboratories/tools-instruments/smart-manufacturing-systems-sms-test-bed)
connects design, fabrication and inspection and publishes manufacturing data
through a volatile MTConnect stream, a queryable repository and technical data
packages. These channels motivate consistency, restart recovery and package
integrity incidents. The new protocols and software faults are authored examples,
not documented NIST failures or claims of full MTConnect conformance.

[Production Analysis with Process Mining Technology](https://figshare.com/articles/dataset/Production_Analysis_with_Process_Mining_Technology/12697997?file=24045434)
provides production event records. We inspected the publisher's
[article metadata](https://api.figshare.com/v2/articles/12697997) and the CSV header
inside file 24045434. It contains case, activity, resource, start and completion
timestamps, work-order quantity, completed/rejected/MRB quantities and rework.
The new workflow models, ambiguity contracts and correction protocols extend
this context; they are not supplied ground-truth models from the dataset.

The [UCI hydraulic condition-monitoring dataset](https://archive.ics.uci.edu/dataset/447/condition+monitoring+of+hydraulic+systems)
has 2,205 experimental 60-second cycles, multirate pressure/power/flow/temperature
and vibration channels, and component condition and stability labels. The stable
flag is zero for stable conditions. UCI reports no missing values. Missing samples,
quality gates and monitoring pipeline defects in our tasks are explicitly
synthetic extensions. No raw dataset rows or external software are redistributed.

## Task scope and distinction from existing tasks

| Task | Context | Repair objective | Why a local boundary fix is insufficient |
| --- | --- | --- | --- |
| R29 | NIST SMS | Recover publication across multiple independently committed channels | Coordinate a durable outbox, delivery receipts, retries and revision visibility after injected crashes. |
| R30 | NIST SMS | Install a complete, verified technical data package | Resolve exact revisions through a dependency graph, detect conflicts/cycles, validate content, and publish atomically. |
| R31 | NIST SMS | Recover consistent snapshots from independent telemetry sources | Couple epoch changes, buffered replay, per-source progress and snapshot visibility across recovery. |
| R32 | NIST SMS | Resume and publish a verified bulk ingestion session | Separate staged data from visible data while validating chunk identity and completeness across restart and conflicts. |
| F25 | Production process mining | Replay a token-based manufacturing workflow | Search silent transitions and repeated labels through parallel branches while enforcing a complete final marking. |
| F26 | Production process mining | Reconstruct ambiguous operation lifecycles | Consider globally compatible start/complete matchings and preserve uncertainty instead of choosing a greedy pair. |
| F27 | Production process mining | Rebuild WIP after production-event corrections | Reconcile revisions and replay causal multi-input quantity transitions without exposing partial material movements. |
| A29 | Hydraulic monitoring | Compute cycle-local multirate hydraulic features | Reconcile signal grids, joint validity, physical integration and coverage decisions as one pipeline. |
| A30 | Hydraulic monitoring | Fit and apply a monitoring baseline without leakage | Enforce temporal/run separation and healthy stable selection before training-only scaling and multivariate scoring. |
| A31 | Hydraulic monitoring | Produce reliable spectral diagnostic decisions | Apply detrending, windowing, spectral normalization and missing-data decision gates in the correct order. |

The closest existing tasks isolate an operation: a sequence cursor, a transaction,
a calibration lookup, a nearest-sample alignment, an interval calculation or a
fixed rework state machine. These additions require agreement between multiple
modules and mechanisms. The contracts explicitly bound search sizes and define
ties and numerical output conventions so that difficulty comes from reasoning
about interactions, not unspecified behavior or excessive runtime.

Every new task includes at least three fault sites across at least two modules,
four plausible incorrect repairs, four public cases and ten hidden cases. Public
examples expose observable symptoms. Hidden checks exercise distinct interactions
and preservation of already-correct behavior. Expected results are independently
specified; tests do not obtain their expected values by running the reference
implementation.

## Splits and version preservation

R29, F25 and A29 are development tasks. R30-R32, F26-F27 and A30-A31 are reserved
evaluation tasks. They introduce separate issue families; the 80 original tasks
retain their exact bytes, IDs and split assignments.

The active split is 12 `demo_dev`, 23 `dev` and 55 `test`. The original release
manifest remains at `benchmarks/tsmc/releases/manufacturing-80-v1.json`. Release
verification pins that archive and rejects changes to any original fixture.
Default preparation exports only development tasks; reserved solver exports
still require explicit `--export-test`.

The expanded design distribution is 23 easy, 43 medium, 12 hard and 12 unrated.
Four hard tasks are on the development side and eight are reserved. Keep original
48-task and expanded 55-task evaluation scores separate when comparing runs.

## Validation

Run trusted baseline, reference, repeated reference and incorrect repair variants
through the authoring checks, then through the native Docker evaluator. The
reference must pass the entire public/hidden suite twice. The baseline and every
incorrect repair must fail, with consistent test discovery and no skipped cases.
No model-driven tuning on the seven new reserved tasks is part of this expansion.

The [native extension audit](../../benchmarks/tsmc/reports/native_hard_10_validation.json)
records 79 Docker executions over 209 new tests and 49 incorrect repairs. Every
incorrect repair fails at least one hidden test. Original 80-task validation is
retained separately because its fixture bytes have not changed.

See the [scale assessment](tsmc_bench_scale.md) for release counts and validation
limitations. Model calibration should use development tasks first,
with a fixed solver, prompt and budget before evaluating the reserved split.
