# TSMC model and reasoning effort experiment

This experiment compares 23 OpenAI model and effort settings on the same ten
development tasks. Each setting has one JSON file containing all ten trial
records, native grading outcomes and aggregate metrics. The reserved test split
is excluded.

The current v3 release uses version 2.0 for this selection's medium and hard
tasks. The [development revision](tsmc_bench_development_revision.md) records the
scope and initial Luna/none calibration. Keep v2 and v3 experiment directories
separate; task IDs alone do not identify identical problem contents.

| Difficulty | Tasks | Count |
| --- | --- | --- |
| Easy | A05, F05, R05 | 3 |
| Medium | A12, F11, R13, R21 | 4 |
| Hard | A29, F25, R29 | 3 |

GPT-5.6 Sol, Terra and Luna each run `none`, `low`, `medium`, `high`, `xhigh` and
`max`. GPT-6 Astra runs `low`, `medium`, `high`, `xhigh` and `max`. The `gpt-5.6`
alias is excluded because it refers to Sol, leaving 23 settings and 230 scored
trials. These are API effort values, not Codex application settings.

All settings use the same native Responses API adapter, instructions, bash tool,
public repository inputs, submission collector and independent Docker grader.
The limits are 50 agent steps and 600 seconds per trial, including subprocess
and solver-container startup. The per-request output limit is 32,768 tokens,
including reasoning. The experiment uses standard service, disables automatic
request retries, and disables the monetary cutoff to avoid truncating more
expensive models earlier. Six condition workers each solve and then grade their
tasks sequentially. A fixed shuffle determines condition and task order.

Before each condition's ten scored tasks, the same configuration runs a full
F01 smoke: solve, collect the workspace patch, and grade it in a fresh container.
The gate requires a nonempty patch, a native grading result, response usage,
complete cost accounting, and timing. The smoke need not solve F01 to demonstrate
that the pipeline reports an incorrect answer correctly. Smoke scores and costs
are recorded separately from the ten-task comparison.

## Run and inspect

The OpenAI key remains in the existing mini-SWE-agent global `.env` or the host
environment. Credentials are never placed in YAML, JSON reports or task containers.
Prepare the TSMC public dataset and local task images using the main benchmark
guide before starting the experiment.

```bash
uv run python -m swebench.benchmarks.tsmc.experiment \
  --output logs/experiments/tsmc-openai-matrix-20260912 --workers 6
```

Use `--prepare-only` to freeze and inspect the experiment without paid inference.
Use `--smoke-only` to stop after the condition smokes. `--condition
gpt-5.6-luna__medium` selects one condition; the frozen experiment still retains
all 23 settings. Filters never silently change the score denominator.

```bash
uv run python -m swebench.benchmarks.tsmc.experiment \
  --output logs/experiments/tsmc-openai-matrix-20260912 --resume
```

Resume verifies public inputs and implementation hashes, skips completed trials,
and resumes grading when inference already finished. A claimed trial with no
final timing artifact is reported as interrupted; it is never silently charged
again. An operating-system lock prevents overlapping drivers. Native grading
checks patch identity, and locks for each instance prevent concurrent graders
from sharing logging handlers.

Artifacts under the output directory:

- `manifest.json`: frozen tasks, images, configs, implementation hashes and prices.
- `conditions/gpt-5.6-luna__medium.json`: one setting's smoke, ten tasks and summaries.
- `summary.json`: comparison index and separate scored/smoke accounting totals.
- `trials.csv`: all 230 formal task slots, including pending or failed attempts.
- `trials/<condition>/<instance>/`: trajectory, predictions, request journal,
  timing, native evaluation reference and final trial record.
- `smokes/<condition>/<instance>/`: separately recorded F01 smoke evidence.
- `sessions.json`: elapsed wall time for each driver invocation.

## Reading the measurements

`resolved` is the independent native grader's boolean, not the solver's claim.
Condition accuracy is resolved tasks divided by ten; separate failure categories
identify API failures, timeouts, empty submissions and grading failures.
`grading_accuracy` reports the resolved fraction among trials with actual test
outcomes. Pending results are explicitly provisional. Public-test success alone
does not establish correctness.

`inference_seconds` covers subprocess startup and solving. `solve_total_seconds`
also includes owned-container cleanup. `grading_seconds` measures grading
separately, and `total_seconds` adds solve/cleanup and grading. Waiting for a
grading lock is separate. Summed task time differs from elapsed experiment time
because tasks run concurrently.

Usage records include input, cached input, cache writes, output, reasoning and
total tokens, plus the returned model and response identifiers. Cached input is
a subset of input; reasoning is a subset of output. Neither is added twice.
The request journal flushes a start record before network I/O and a terminal
record after response or failure, so a killed request remains visible.

Costs use API-reported counters and the pinned official standard prices verified
on September 12, 2026. Cache reads, writes and the long-context multipliers are
accounted for. These are usage-based estimates, not invoices. Missing response
usage remains unknown: `estimated_cost_usd` is null when incomplete, while
`observed_cost_usd` retains the known subtotal. Smoke and diagnostic spending
must be included when reporting total experiment expenditure.

The task difficulties are author estimates. A single run of ten selected
development tasks can compare this sample's outcomes, latency and cost; it does
not measure full-benchmark accuracy or establish reliable difficulty levels.

Official references: [GPT-5.6 Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol),
[GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra),
[Responses API guidance](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra),
and [API pricing](https://developers.openai.com/api/docs/pricing).
