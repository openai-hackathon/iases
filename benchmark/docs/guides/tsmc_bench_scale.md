# TSMC-bench scale, difficulty and evaluation split

Assessment date: 2026-09-12. This release contains **90 authored repair tasks**
in an imagined semiconductor factory. Manufacturing references broaden the
scenarios beyond semiconductor terminology. These are small synthetic repositories,
not historical production incidents.

## Frozen inventory

| Dimension | Release |
| --- | --- |
| Tasks | 90: F01-F27, A01-A31, R01-R32 |
| Tracks | 27 factory logic, 31 data analysis, 32 reliability |
| Splits | 12 original `demo_dev`, 23 additional `dev`, 55 reserved `test` |
| Required tests | 1,190: 451 public, 739 hidden from solver workspaces |
| Baseline classifications | 486 FAIL_TO_PASS, 704 PASS_TO_PASS |
| Evaluator gates | 90 additional complete-suite gates |
| Incorrect variants | 209: two per original task, four to six per new hard task |
| Validation protocol | Baseline, reference, repeated reference, all mutants: 400 original + 79 extension Docker executions |
| Scenarios | Four existing composition replays using the original 12 tasks |

Original task fixtures and their provenance are unchanged. The 78 additions to the original 12 use authored
implementations and contracts, sharing a CLI and test scaffold. Task count does
not imply equivalent independent repository diversity.

[`release.json`](../../benchmarks/tsmc/release.json) freezes membership, related
issue families, test partitions, source references and SHA-256 hashes. Preparation
rejects drift. Task revisions require an explicit new release. The archived 80-task manifest and
all its fixture hashes are preserved in v2.

## Difficulty policy

`design_difficulty` is an author estimate. `difficulty` / `measured_difficulty`
remain `unmeasured`: reference and mutant tests do not establish a calibrated
model difficulty ranking.

| Cohort | Easy | Medium | Hard | Unrated |
| --- | ---: | ---: | ---: | ---: |
| Original 12 | 0 | 0 | 0 | 12 |
| First 44 new tasks | 18 | 26 | 0 | 0 |
| Later 24, after the policy update | 5 | 17 | 2 | 0 |
| Original 80-task release | 23 | 43 | 2 | 12 |
| Requested hard extension | 0 | 0 | 10 | 0 |
| Entire 90-task release | 23 | 43 | 12 | 12 |

The user's **20% easy / 70% medium / 10% hard** target applies to subsequent
authoring, without rebalancing completed tasks. Largest-remainder rounding yields
5/17/2 for the final 24. Do not describe the entire release as 20/70/10.

Easy tasks cover boundaries, units and identity. Medium tasks combine ordering,
state, joins, ownership or failure handling, including real asyncio cancellation
and SQLite DDL rollback. F19 and R22 each require repairs in two modules: constrained
allocation plus snapshot commit, and durable epoch allocation plus stale-writer
fencing. Their two mutants are partial fixes, both rejected by the tests.

The hard extension adds three development and seven reserved tasks. The active
release therefore has four development and eight reserved hard tasks. This is a
small subgroup, and its difficulty remains unmeasured. See the
[extension designs and source evidence](tsmc_bench_hard_extension.md).

## Reserved evaluation protocol

Use `demo_dev` and `dev` for API, prompt and agent iteration. Keep `test` out of
model-driven tuning. Author reference validation on `test` is necessary and is
distinct from solver calibration. Report the 55-task test score with a fixed
denominator, including empty patches and timeouts.

Related expiration, unit-scaling, interval-union and record-aggregation variants
stay on the development side. During author review, F06, R12 and R20 exchanged
splits with related development-side tasks, before any model runs on the expansion.
The curated family grouping does not prove semantic independence or absence of
pretraining contamination.

Default solver exports include only `demo_dev` and `dev`. `--export-test` creates
a separate `heldout-public` directory. Both exports omit gold and private tests.
The native task repo, evaluation parquet and trusted author checkout contain
answers; publishing the entire checkout would remove their secrecy.

## Empirical evidence

The original 12 tasks were attempted three times through the user-supplied
endpoint, alias `local`, server-reported root `Qwen/Qwen3-8B-FP8`, mini-SWE-agent
2.4.6, two workers, 40 steps and an 8-minute agent budget. Native grading resolved
**0/12 in each run**, retaining all tasks in the denominator. Each of the first two
runs produced only one nonempty patch; neither passed. The third run included
API and context failures. Empty submissions and shell-editing mistakes dominated.

These observations cannot establish that the original tasks are hard or that the
new tiers discriminate well. Model capability, text-command interaction and endpoint
reliability are confounded. No model was run on the reserved tasks in either release. Before
claiming empirical discrimination, compare more than one capable solver on fixed
development tasks and budgets, preserving repeated outcomes and failure causes.

The OpenAI Luna smoke check solved original F01 in six calls and passed independent
evaluation. It confirms the corrected submission path on one development task,
not calibrated difficulty.

A separate 10-task timing experiment uses 50 steps and a hard 10-minute outer
limit. Its execution-duration report is not a difficulty calibration.

## Comparison with SWE-bench

| Set | Evaluation instances | Origin |
| --- | ---: | --- |
| This TSMC-bench release | 55 reserved, plus 35 development | Authored manufacturing software |
| SWE-bench Lite | 300 | Real issue/commit pairs from 11 Python repositories |
| SWE-bench Verified | 500 | Human-reviewed real issues |
| SWE-bench Full | 2,294 | Real issue/commit pairs from 12 Python repositories |

Counts come from the official [Lite description](https://www.swebench.com/lite.html)
and [Verified dataset](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified).
The comparable TSMC evaluation denominator is 55, not 90. One result changes its
score by 1.82 percentage points, versus 0.33 for Lite and 0.20 for Verified.
Different task distributions and repository complexity prevent direct comparison
of leaderboard percentages.

90 tasks support a focused pilot. Preserve the original 48-task denominator when
comparing experiments that predate the extension. Further growth should prioritize larger
integration surfaces, distinct incidents and development results from multiple
capable solvers. More seeds or renamed fixtures do not increase repair diversity.
Current scenarios still replay precomputed patches rather than measure live
restoration strategy. See [manufacturing references](tsmc_bench_sources.md) for
selected datasets and the distinction between source context and authored faults.
