# Seven development-task revisions

The `manufacturing-90-v3` release replaces only the four medium and three hard
tasks in the existing ten-task pilot. They retain their task IDs and development
assignments, and receive instance version `2.0`. The three selected easy tasks
and all other 80 tasks retain their exact contents and identities. This includes
all 55 reserved evaluation tasks.

The preceding Luna/none pilot solved all ten original tasks. Its difficult tasks
often supplied an almost complete algorithm with a few incorrect comparisons.
Adding more examples of those comparisons would provide little evidence of a
meaningful difficulty increase. These revisions require repairing interacting
behaviors and replacing incomplete algorithms.

| Task | Design difficulty | Revised repair |
| --- | --- | --- |
| A12 | Medium | Historical metrology joins with revision visibility, quality corrections and calibration validity |
| F11 | Medium | Continuous workstation booking across operating calendars, maintenance and weighted capacity reservations |
| R13 | Medium | Scoped asynchronous singleflight ownership, invalidation and cancellation lifecycle |
| R21 | Medium | Scoped command idempotency, typed payload equivalence and transactional outcome replay |
| A29 | Hard | Clock-corrected multirate hydraulic windows, calibration boundaries and retractions after late corrections |
| F25 | Hard | Globally optimal process alignments with weighted markings and partially ordered observations |
| R29 | Hard | Durable ordered publication with lease fencing, consumer gaps, crash recovery and safe compaction |

Medium tasks combine several rules within one bounded service operation. Hard
tasks additionally require reasoning across a state space, continuous signal
segments or independently durable participants. These are design hypotheses;
implementation size and test counts do not by themselves establish difficulty.

## Operational sources and authored assumptions

The scenarios are synthetic software repairs in an imagined semiconductor
factory. They do not claim to reproduce TSMC incidents or defects in the source
datasets. No original source code or raw dataset rows are bundled.

- [ERPNext workstation-capacity repair](https://github.com/frappe/erpnext/pull/53523)
  supplies a real example of incorrect overlapping production-capacity checks.
  F11 uses an independently authored calendar and booking interface.
- [NIST manufacturing test-bed integration](https://www.nist.gov/publications/connecting-deploying-and-using-smart-manufacturing-systems-test-bed)
  supplies the context of equipment-data collection, curation and reuse across
  factory systems.
- [Production Analysis with Process Mining Technology](https://doi.org/10.4121/uuid:68726926-5ac5-4fab-b873-ee76ea412399)
  supplies production-event context. F25's observation groups, bounded Petri net
  and alignment cost policy are explicitly authored abstractions.
- [UCI hydraulic condition monitoring](https://archive.ics.uci.edu/dataset/447/condition+monitoring+of+hydraulic+systems)
  supplies multirate pressure and flow measurement context. Historical corrections,
  clock anchors, changing calibration and retractions are authored extensions.
- [Python task cancellation and shielding](https://docs.python.org/3/library/asyncio-task.html)
  informs the asynchronous lifecycle in R13.
- [Transactional outbox](https://microservices.io/patterns/data/transactional-outbox.html)
  describes atomic publication intent, ordering and duplicate relay delivery.
  R21 and R29 define their own bounded command and recovery protocols.

Public contracts state the required behavior, valid input domain and tie rules.
Hidden tests exercise that same contract; they do not require an undisclosed
algorithm or a particular reference patch. Reference fixes and deliberately
incomplete repairs stay in author-only material.

## Preservation and validation

The v2 manifest is archived at
`benchmarks/tsmc/releases/manufacturing-90-v2.json`. The seven original task
directories are preserved under `releases/manufacturing-90-v2/tasks/`.
The v3 verifier checks the pinned v2 manifest, every archived original, and all
unchanged task files and metadata. A partial migration, changed reserved fixture
or reuse of a version 1.0 identity is rejected. The original v1 archive and its
validation evidence are retained as well.

Before solver inference, validate each broken baseline, reference repair twice,
and multiple plausible incomplete repairs in the native Docker grader. Baselines
and incomplete repairs must fail; reference repairs must pass every required
test. These checks establish a usable oracle, not model difficulty.

The completed native audit records 79 executions over 203 required tests: all
seven baselines fail, all 14 reference runs pass, and all 58 incomplete repairs
fail hidden tests. Evidence is in
`benchmarks/tsmc/reports/native_development_revision_validation.json`.
R29 checks observable crash/restart behavior; the functional grader is not an
adversarial proof of a submitted implementation's physical storage architecture.

## Development calibration

Run Luna/none first on the same ten task IDs, with the unchanged public-only
solver interface, 50-step limit and 600-second limit. Run the full F01 smoke
before the ten scored trials. Preserve a separate experiment directory and
condition JSON; never overwrite or combine the original pilot's task results.
The API adapter, submission collector, grader and pricing methodology are the
same as in the model-effort experiment.

```bash
uv run python -m swebench.benchmarks.tsmc.prepare \
  --output .generated/tsmc-revision
uv run swebench images build .generated/tsmc-revision/task-repo -n swebench -j 2 \
  -i tsmc__a12-v2.0 -i tsmc__f11-v2.0 -i tsmc__r13-v2.0 \
  -i tsmc__r21-v2.0 -i tsmc__a29-v2.0 -i tsmc__f25-v2.0 -i tsmc__r29-v2.0
uv run python -m swebench.benchmarks.tsmc.validate \
  --task-repo .generated/tsmc-revision/task-repo \
  --run-id tsmc-development-revision-7 --workers 2 \
  --task A12 --task F11 --task R13 --task R21 --task A29 --task F25 --task R29
uv run python -m swebench.benchmarks.tsmc.experiment \
  --dataset .generated/tsmc-revision/public \
  --task-repo .generated/tsmc-revision/task-repo \
  --output logs/experiments/tsmc-development-revision-20260912 \
  --run-id tsmc-development-revision-20260912 --workers 1 \
  --condition gpt-5.6-luna__none
```

The unchanged F01 smoke and three easy-task images must also exist, as in the
preceding experiment. A fresh installation can build those explicitly or build
the entire task repo.

Compare total and per-difficulty resolution counts, per-task elapsed time,
input/output/cached/reasoning tokens and estimated USD. Treat API failures and
missing telemetry separately from incorrect repairs. The condition denominator
is ten, while the matrix-wide denominator remains 230 with unrun settings
explicitly pending. Use the condition JSON for this calibration's accuracy.

A single run of three hard and four medium development tasks cannot establish a
reliable difficulty distribution or full-benchmark accuracy. Do not relabel the
reserved tasks or tune them using these outcomes. Further repetitions and model
comparisons are needed to establish stable discrimination.

## Initial rerun

Luna/none completed all ten revised-selection trials with nonempty submissions,
native grading and complete usage/cost records. There were no failed API requests.

| Design difficulty | Original pilot | Revised pilot |
| --- | --- | --- |
| Easy | 3/3 | 3/3 |
| Medium | 4/4 | 3/4 |
| Hard | 3/3 | 1/3 |
| Total | 10/10 | 7/10 |

The three failures were incomplete repairs: R21 omitted expected revision from
command identity; A29 missed clock-scaled gap and joint-support coverage rules;
R29 retained stale-token acceptance in lease operations. Each passed its public
tests but failed required hidden tests from the documented contract.

The ten scored tasks took 247.05 seconds of session wall time, used 267,994 tokens
and cost an estimated USD 0.02926851. The separate smoke took 23.84 seconds and
USD 0.001648; total recorded expenditure was USD 0.03091651. Per-task time, cost,
token breakdowns, failure IDs and the archived-pilot comparison are preserved in
`benchmarks/tsmc/reports/luna_none_development_revision_20260912.json`.
This single run provides initial evidence of a difficulty gap; it does not
establish stable success-rate estimates or a ranking across models.
