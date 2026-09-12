# Solver and submission workflow

A solver must inspect and edit the actual repository. A completion message is a
request to submit; only the separate evaluator can establish that an issue is
resolved. SWE-bench and TSMC-bench share the same patch-based boundary.

## Workflow

1. Start an isolated workspace at the task's original commit. Give the solver the
   issue, public source and public tests, without reference patches or private tests.
2. Let the solver inspect the implementation, reproduce the issue, edit files,
   run relevant tests and revise its changes within the fixed step and time budgets.
3. Collect the actual workspace diff against the original commit and write it to
   the prediction's `model_patch` field. Preserve the model's original response.
4. Apply that patch to a fresh evaluation workspace. Run the evaluator's tests and
   grade the expected FAIL_TO_PASS and PASS_TO_PASS cases.

Public test results help the solver but do not replace independent evaluation.
TSMC additionally enforces its allowed paths and complete required suite.

## Why the earlier submissions were empty

The original TSMC prompt required the model to stage its changes and print
`git diff --cached` output. Some attempts immediately ran the completion command
without editing. Another inspected files but did not implement a repair. In one
inspected attempt, the model wrote files but did not stage them, so the submitted
diff was empty even though the workspace had changed. That attempted repair also
failed its public tests: collecting it correctly would not establish success.

These are separate failures: no repair, omitted changes, and incorrect repair.
Endpoint errors and environment failures add further causes. A zero score with
empty patches cannot establish that the benchmark itself is too difficult.

## Automatic collection

`benchmarks/tsmc/configs/agent.yaml` enables `run.collect_workspace: true`.
Other configurations can enable the same runner with `swebench infer
--collect-workspace`. The wrapper supports mini-SWE-agent 2.4.6.

The collector uses a temporary Git index, preserving the model's real index. It
includes tracked edits, deletions, staged additions and changes committed after
the original baseline. TSMC also includes untracked `fabops/*.py` and
`tests/test_agent_*.py`. For other repositories, new files must be staged.
Untracked scratch files such as `patch.txt` are excluded by default. Tracked
changes are not silently filtered; the evaluator still checks their validity.

An empty completion attempt receives an observation explaining that source
changes are required. It continues within the existing budget without resetting
the step counter. This does not force a correct solution or permit extra steps.

Trajectories retain `model_submission`, `model_exit_status`, `patch_baseline`,
`submission_source`, rejected completion attempts and the collected `submission`.
Model errors and step-limit exits still trigger collection. The bounded timing
runner also attempts collection after terminating a timed-out subprocess, before
removing its labeled container. Recovery failure is explicitly recorded.

`Submitted` means that the agent ended with a nonempty workspace diff. It does not
mean the tests passed. `NoChanges`, `LimitsExceeded`, `HardTimeout`,
`PatchCollectionError`, and invalid, missing or incomplete trajectories remain distinct.

## OpenAI provider

The existing mini-SWE-agent runner can call the OpenAI API directly. This uses
the same workspace collector and evaluator; it does not use the Codex CLI.
The provider overlay is `benchmarks/tsmc/configs/openai.yaml`. Apply it after
`benchmarks/tsmc/configs/agent.yaml` and select an OpenAI model explicitly.
Use these two configurations together instead of an old Modal/vLLM run config.

Store `OPENAI_API_KEY` in mini-SWE-agent's global `.env` file. Its location is
printed by `uv run mini --help`; on this macOS checkout it is
`/Users/rich/Library/Application Support/mini-swe-agent/.env`:

```dotenv
OPENAI_API_KEY=your_actual_api_key
```

Alternatively, export `OPENAI_API_KEY` in the shell that starts inference.
Already exported variables take precedence over mini's global `.env`.
The `swebench infer` command also loads a checkout `.env` before mini starts;
avoid maintaining conflicting copies of the key. Keep credentials out of YAML
because mini saves model configuration in trajectories. The provider overlay
sets the official API base explicitly and leaves the key in the host environment.
The task container receives no forwarded environment variables.

Select a model available to your OpenAI project, replacing the placeholder below.
It must support Chat Completions with function calling and have cost metadata in
the installed LiteLLM version. No paid model is selected by the overlay.

```bash
uv run swebench infer .generated/tsmc/public -s demo_dev \
  -c benchmarks/tsmc/configs/agent.yaml \
  -c benchmarks/tsmc/configs/openai.yaml \
  --model openai/YOUR_OPENAI_MODEL \
  --run-id tsmc-openai-f01 -w 1 \
  --filter '^tsmc__f01-v0\.2$' --dry-run
```

Remove `--dry-run` to start inference. For a hard per-task limit of 50 steps and
600 seconds, use the timing runner instead. The following samples one development
task, runs one round, and includes subprocess and container startup in the timeout:

```bash
uv run python -m swebench.benchmarks.tsmc.timing \
  --dataset .generated/tsmc/public --split demo_dev \
  --config benchmarks/tsmc/configs/agent.yaml \
  --config benchmarks/tsmc/configs/openai.yaml \
  --model openai/YOUR_OPENAI_MODEL \
  --output logs/inference/tsmc-openai-single-01 \
  --count 1 --workers 1 --rounds 1 --steps 50 --timeout 600 --seed 20260912
```

Use a fresh output directory for each timing run. `--seed` controls task sampling;
it is not sent to the model API. Only set `--model-seed` when the selected provider
and model support it. `--endpoint` is optional and overrides the configured API
base; omit it when using the official OpenAI overlay. The runner preserves the
configured model interface and does not add vLLM-specific request parameters.
The TSMC configuration retains its per-agent cost limit in addition to step and
time limits. Costs are tracked using LiteLLM metadata and checked between calls,
so this is not an exact billing cap.

The `benchmarks/tsmc/configs/openai-luna.yaml` overlay selects `gpt-5.6-luna`
with `reasoning_effort: medium` and a 16,384 completion-token limit, including
reasoning tokens. Apply it after `openai.yaml` and omit the placeholder `--model`
argument in the examples above. It contains no credentials. The single-task
workflow check uses the original F01 development task, not the heldout split.

The [live Luna workflow record](../../benchmarks/tsmc/reports/openai_luna_f01_20260912.json)
documents a successful F01 run: six API calls, 27.7 seconds for inference and
workspace cleanup, a 651-byte automatically collected patch, and independent
evaluation passing all 18 tests (five public and 13 hidden) plus the suite gate.
The prediction and graded patch match the collected diff exactly. This verifies
one development workflow; it does not measure accuracy over the 80-task release.

For grading, pass the generated `inference/preds.json` for the task to
`swebench eval`, as described in the [TSMC-bench guide](tsmc_bench.md).
An accepted API request, a nonempty submission, and a resolved task are separate
checks; only independent evaluation establishes the last one.

See the [OpenAI quickstart](https://developers.openai.com/api/docs/quickstart)
and [mini-SWE-agent model setup](https://mini-swe-agent.com/latest/models/quickstart/)
for credential and model configuration details.

## Environment failures and validation

The timing runner checks free host disk space before starting inference (1 GiB by
default, configurable with `--min-free-mb`). This is a minimum for run artifacts,
not a capacity estimate for downloading Docker images. Trajectories and timing
artifacts use temporary files followed by replacement, preserving the previous
complete artifact if a new write fails. This cannot make a full disk writable or
recover an unavailable Docker engine.

Tests exercise unstaged and new-file collection, application to a clean baseline,
committed changes, preservation of the real index, early empty completions,
unchanged step budgets, model failures, hard-timeout recovery before container
removal, and interrupted artifact writes. These are harness checks, not model
accuracy measurements. No new task downloads are needed to run them.

A controlled Docker regression exercised five agent steps on the original F01
fixture: reject an empty completion, observe failing public tests, apply a trusted
reference without staging, run passing public tests, and submit. The collected
patch passed independent native evaluation. The
[validation record](../../benchmarks/tsmc/reports/solver_submission_validation.json)
contains the image and patch hashes. This scripted check made no model API requests.
