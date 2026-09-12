# TSMC-bench

TSMC-bench uses this checkout's native task repo, dataset, Docker evaluation and report commands. Its 90 manufacturing repair tasks accept the same predictions format as SWE-bench. Four incident scenarios add service recovery checks through `swebench scenario` using the original 12 tasks. The current v4 release strengthens [nine hard tasks](tsmc_bench_hard_revision.md), preserving A29, F25, R29 and every other unselected task. It follows the v3 revision of [seven selected development tasks](tsmc_bench_development_revision.md). Previous manifests and replaced fixtures are archived under `benchmarks/tsmc/releases/`.

The splits are 12 original `demo_dev`, 23 additional `dev`, and 55 reserved `test` tasks. Requirements, contracts, notes, comments and scenario descriptions are in English. Original fixtures retain their provenance; the expansion is frozen in `benchmarks/tsmc/release.json`. All incidents are synthetic, with an imagined semiconductor-factory setting.

The [ten-task hard extension](tsmc_bench_hard_extension.md) adds four infrastructure, three process and three sensor-analysis incidents while preserving the original release.

See the [scale and difficulty assessment](tsmc_bench_scale.md) and [manufacturing references](tsmc_bench_sources.md) for inventory, split policy, source selection and calibration limitations.

## Build and evaluate

Run these commands from the repository root with Python 3.10+ and Docker available. The examples use the checkout's `uv` environment. Containers use Linux/amd64, Python 3.13.9 and pytest 9.0.2; Apple Silicon requires Docker's amd64 emulation.

```bash
uv sync --python 3.13 --frozen
uv run python -m swebench.benchmarks.tsmc.prepare
uv run swebench dataset check .generated/tsmc/task-repo
uv run swebench dataset build .generated/tsmc/task-repo -o .generated/tsmc/evaluation
uv run swebench images build .generated/tsmc/task-repo -n swebench -j 2

uv run swebench eval .generated/tsmc/evaluation/TSMC-bench -s demo_dev \
  --task-repo .generated/tsmc/task-repo --gold --run-id tsmc-gold -j 2
uv run swebench report tsmc-gold
```

The `-n swebench` image namespace must match task metadata. The Python base image uses a pinned amd64 manifest digest, and pytest dependencies have fixed versions. APT packages still come from the Debian repository; retain complete image IDs with experimental results.

For a first run, add `--task F01` to prepare. Prepare replaces its complete generated output, so run `dataset build` again afterward. It refuses to overwrite a nonempty directory without its generator marker.

After changing task sources, add `--force-rebuild` to `images build`: the image builder otherwise skips existing tags. The TSMC validator and scenario runner reject images whose baseline label does not match the generated task.

| Path | Contents and audience |
| --- | --- |
| `benchmarks/tsmc/tasks/` | Canonical author-maintained task source |
| `.generated/tsmc/task-repo/` | Native metadata, Docker contexts and private evaluator |
| `.generated/tsmc/public/` | Solver parquet with `image_name`, baseline commit and problem statement |
| `.generated/tsmc/heldout-public/` | Reserved solver tasks, created only with explicit `--export-test` |
| `.generated/tsmc/evaluation/TSMC-bench/` | Evaluator parquet, including gold, tests and eval script |
| `logs/evaluation/<run-id>/` | Native patches, test outputs and grading reports |

## Connect a solver API harness

Read the public dataset, create a separate workspace from each task's `image_name`, modify code in `/testbed`, and return a unified diff against `base_commit`. SWE-bench and TSMC-bench share this JSONL format:

```json
{"instance_id":"tsmc__f01-v0.2","model_name_or_path":"my-api-harness","model_patch":"<unified diff including new files>"}
```

JSON arrays and mappings keyed by instance ID are also supported. `model_patch` must contain the diff text, not a file path. Stage new files before collecting the diff; ordinary `git diff` omits untracked files. The scenario runner rejects duplicate JSON keys, duplicate instances, conflicting mapping IDs, invalid record types and nonfinite numbers. A nonempty predictions file must match at least one scenario instance; records for other scenarios may coexist in the same file.

Allowed changes are Python files under `fabops/` and new `tests/test_agent_*.py`. Existing public tests, docs, data and configuration are protected. Symlinks, executable files, binary patches, conftest, sitecustomize, usercustomize and result_plugin are forbidden. Each task's public documents define the complete contract.

```bash
uv run swebench eval .generated/tsmc/evaluation/TSMC-bench -s demo_dev \
  --task-repo .generated/tsmc/task-repo \
  -p /path/to/preds.jsonl --run-id tsmc-api-001 -j 2
uv run swebench report tsmc-api-001
```

A Codex API harness is planned as the next solver integration. The common interface is implemented; a Codex client and live incident scheduler are not. The existing `swebench infer` path can use `benchmarks/tsmc/configs/agent.yaml`; model and provider settings come from an external run configuration. Development-only API pilots are recorded separately.

For direct OpenAI API access, apply `benchmarks/tsmc/configs/openai.yaml` after the
agent configuration. See [OpenAI provider setup](solver_submission.md#openai-provider)
for key storage, model selection, a single-task command and bounded timing runs.

The bundled TSMC configuration enables automatic workspace collection. It collects
tracked edits, staged new files, and permitted new TSMC Python files against the
original commit. The model does not need to construct or print its patch. Empty
completion attempts receive feedback within the original budget. See the
[solver and submission workflow](solver_submission.md) for status semantics,
timeout recovery, and the distinction between submission and resolution.

Use `-s dev` for the 23 additional development tasks. Default solver exports contain no
`test` split. When the solver and budgets are fixed, create a separate reserved
export with `python -m swebench.benchmarks.tsmc.prepare --export-test`, then rebuild
the evaluation parquet. Run inference on `.generated/tsmc/heldout-public -s test`
and grade against the private evaluation dataset using `-s test`. Keep author
sources, native task repos and evaluation parquets outside solver access. Frozen
source changes are rejected; use an explicit new release for task revisions.

## Grading rules

A TSMC task is resolved only when its patch respects the allowed paths, the collected required test IDs match the manifest exactly, every required test passes, pytest and the process exit successfully, and no timeout occurs. Skips, xfails, missing IDs and duplicate IDs cannot pass.

The release has 1,419 cases: 641 FAIL_TO_PASS and 778 PASS_TO_PASS, including the original 226 cases. Each task also gets `tsmc_grader::required_suite`, connecting the complete-suite requirement to the existing SWE-bench grader. These 90 gates are counted separately from task tests.

Images contain only public workspaces and one baseline commit. A Docker context allowlist excludes gold and private tests; the eval script injects private material at evaluation time. The `python_offline` profile disables networking, drops capabilities, and limits CPU, memory and PIDs. Existing SWE-bench tasks without a profile keep their previous settings. Named profiles currently require local Docker.

Raw pytest output is saved as an encoded artifact; only canonical test IDs enter the grading region. This is a functional evaluator. The in-process pytest oracle is not an adversarial security boundary against candidate code deliberately attacking the grader.

The development validator actually executes empty-patch baselines, which ordinary evaluation would filter out:

```bash
uv run python -m swebench.benchmarks.tsmc.validate \
  --run-id tsmc-fixtures-001 --workers 2
```

It runs baseline, gold, gold repeat and every mutant. The nine v4 replacements each have eight to twelve mutants, requiring 115 Docker executions for their author audit. Results are saved to `logs/evaluation/tsmc-fixtures-001/validation.json`. Use a fresh run ID each time. This author audit includes reserved tasks without exposing their feedback to a solver.

## Incident scenarios

```bash
uv run swebench scenario run DC01 --gold --trial-id dc01-gold-001
uv run swebench scenario run DC04 -p /path/to/preds.jsonl --trial-id dc04-api-001
uv run swebench scenario report logs/scenarios/dc04-api-001
```

All four scenarios have executable composition checks. The runner first grades submitted patches with the native Docker evaluator, then invokes `python -m fabops --input ...` in fresh offline containers, passing actual candidate outputs downstream.

| Scenario | Services | Main behavior |
| --- | ---: | --- |
| DC01 | 8 | journal replay feeds telemetry/state/qualification; release feeds reservation; maintenance and downtime consume upstream data |
| DC02 | 6 | workers supply replay capacity; the buffer expires at 120 seconds and initial qualification/release caches at 180 seconds |
| DC03 | 8 | journal/workers feed telemetry, then state/lineage/wafer reports; current machine state controls reservation |
| DC04 | 8 | external source completeness is observed at 60 seconds; state, lineage and wafer reports gate release |

The public composition contract is `tsmc-composition/1.1`, implemented with deterministic fixtures in `swebench/benchmarks/tsmc/scenario/probes.py`:

- Journal preserves complete transport records. Domain payloads provide machine events, qualifications, maintenance, downtime, lineage and wafer rows.
- Telemetry consumes offsets, deduplicates event IDs and verifies batch/incremental equivalence. Its adapter forwards only records covered by the candidate's `seen` output. Workers' actual free slots set the batch size.
- State supplies current machine status; qualification supplies current authorization after revocation. Release exercises eligible positives and held, locked and revoked negatives.
- DC04 maps lineage impacts, missing wafer reports and latest valid tests that do not all pass into quality holds, preserving existing holds.
- Reservation consumes release output or available machines. Its sequential CLI probe supplements R02's required concurrency suite.
- Boolean result arrays must have the exact expected length and boolean values. Alarm conversions use the task contract's absolute tolerance of `1e-9`; invalid and missing measurements must retain null converted values.

Task verification does not imply RESTORED. Recovery also requires current dependencies, environment facts and a successful probe bound to the current patch, service, upstream and fact epochs. Changing an upstream candidate or environment fact invalidates downstream recovery; true -> false -> true requires new evidence too.

The current mode is **precomputed-patch-replay**. By default, supplied patches become available at synthetic time 0 and the observation horizon is 240 seconds. Use `--availability trace.json --horizon 300` with an author-owned service-to-seconds map, for example:

```json
{"workers":30,"telemetry":150,"qualification":200,"release":220}
```

Omitted services default to time 0. Missing predictions and availability beyond the horizon remain unsubmitted and stay in the denominator. Only submitted patches within the horizon require Docker images; an entirely unsubmitted replay can run without Docker. Future author events are absent from public scenario observations. Expiry applies to the initial fallback, not a newly verified alternate path. At each timestamp, all observations and grades are applied before probes, so a same-time revocation cannot produce a transient recovery success.

The runner verifies scenario source mappings against the generated task edition and evaluator configuration before opening Docker. Native grade receipts must match the submitted patch hash, instance and baseline. Malformed probe output is recorded as a failed probe before any recovery state changes.

`logs/scenarios/<trial-id>/` stores the manifest, patches, measured Docker grading times, probe inputs/outputs, hash-chained events and report. Native task logs use run ID `scenario-<trial-id>`. Trials atomically claim that shared run ID, which must be fresh even across different output roots. The report command validates receipt chains and trial boundaries, then rebuilds state and timing without executing candidate code. Hash chains detect accidental edits; they are not author signatures.

Reports separate workflow from business capability. They include per-service time not restored, unavailable time in offline/blocked-safe states, untrusted time in unverified/stale/degraded states, environment-blocked time, first recovery, unsubmitted tasks, grading timeouts, failed probes, and measured grader queue/execution time. Time in limited, buffered and backlog states remains explicit in `capability_seconds`. No arbitrary business weights are added. Synthetic availability is not measured model repair time, and these runs do not measure GPU placement.

## Development validation

```bash
uv run python -m pytest -q tests/test_tsmc_prepare.py tests/test_tsmc_grading.py \
  tests/test_tsmc_inference.py tests/test_tsmc_state.py tests/test_tsmc_scenarios.py \
  tests/test_tsmc_scenario_runner.py \
  tests/test_container_profiles.py
```

Tests cover source provenance, deterministic conversion, public/private export, strict grading, illegal changes, missing/skip/xfail results, timeouts, recovery invalidation, receipt replay and actual bundled CLI composition. Only known baseline/gold fixtures execute on the development host; submitted candidate code executes in Docker.

The complete repository suite also exercises an optional Anthropic import in an existing inference test. Run it with `uv run --with anthropic python -m pytest -q` when that optional dependency is not installed.

The original Docker audit confirmed all 12 gold patches and repeats, rejected all 24 mutants, and reproduced classifications for 226 original tests. DC01-DC04 gold replays exercised every mapped service in Docker. The completed original 80-task audit qualified all tasks across 400 executions; image IDs and outcomes are preserved in `benchmarks/tsmc/reports/native_80_validation.json`. That evidence applies to the unchanged fixtures and archived originals. The v2 ten-task hard extension added 79 native Docker validations, recorded separately in `benchmarks/tsmc/reports/native_hard_10_validation.json`; every incorrect repair also failed hidden tests. The seven v3 replacements receive a separate native audit and development calibration. Exploratory model pilots use development tasks only; no actual factory service deployment has been performed. See the [scale assessment](tsmc_bench_scale.md) for model results and their limitations.
