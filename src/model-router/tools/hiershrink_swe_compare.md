# Budget comparison

Run the diagnostic with cached pilot data. Use a new output directory for each run.

```sh
PYTHONPATH=../icr-router/experiments OPENBLAS_NUM_THREADS=1 ../icr-router/.venv/bin/python tools/hiershrink_swe_compare.py --source ../codex/.cache/hiershrink-swe-pilot --output ../codex/.cache/hiershrink-swe-comparison-v2
PYTHONPATH=tools:../icr-router/experiments ../icr-router/.venv/bin/python -m unittest tools/test_hiershrink_swe_compare.py
```

The runner checks the pilot data hash and split order. It writes its protocol before fitting. It preserves prior artifacts. It uses no network calls. The ridge model learns the high-minus-medium outcome from the original 300 training instances. Both learned rankings use every validation score breakpoint to select the highest resolution rate within the same validation budget. HierShrink retains its prior validation-selected shrinkage, so total tuning resources are not equal.

## Diagnostic result

| Policy | Resolved / 100 | Historical USD |
|---|---:|---:|
| Fixed medium | 68 | 26.19 |
| Fixed high | 71 | 55.40 |
| Ridge gain | 70 | 38.58 |
| Random mixture at ridge cost | 69.27 expected | 38.58 expected |
| HierShrink | 68 | 26.19 |

Ridge gains 0.73 percentage points over the random mixture at its historical cost. Its conditional paired bootstrap 95% interval is [-2.12, 3.73] percentage points. This does not establish an improvement. HierShrink still selects medium for all instances after the finer threshold search.

The random mixture uses the evaluation-set mean action costs to match each policy's cost analytically. It is a descriptive comparator, not a policy calibrated for deployment. Its interval conditions on the fitted policy and mixture fraction. It excludes uncertainty from training, mixture calibration, and repeated agent execution. A mixture outside the two fixed-action mean costs has no matched comparator. The script does not extrapolate.

These costs come from published agent runs. Embedding and router overhead are excluded because they have not been measured. The test outcomes were already inspected before this experiment. All results are exploratory. No policy is deployed.

## Confirmatory protocol for new data

1. Freeze agent version, prompt, tools, retry limits, model versions, effort settings, and cost accounting before collection. Include failures and retries. Record router and embedding overhead separately and include them in total cost.
2. Reserve unseen task IDs before any fitting. Keep every model, effort, and repeat of a task in the same split. Exclude all 500 current pilot task IDs from a fresh holdout. Keep holdout outcomes inaccessible during tuning.
3. Compare fixed actions, a random upgrade policy calibrated on validation, ridge gain, and HierShrink. Declare the budget before holdout evaluation. Give learned methods the same total hyperparameter trial allowance. Count shrinkage and threshold searches in that allowance. Freeze the candidates before training.
4. Select the strongest budget-feasible baseline on validation. Freeze every policy and its random seeds. Report holdout success and actual total cost. Flag budget overruns. Do not describe validation budget compliance as equal realized test cost.
5. Report paired task bootstrap differences against the frozen comparator. Group repeated runs by task. Predeclare one primary budget and comparison. Use other budgets as descriptive results. Require a positive lower confidence bound and budget compliance before claiming an improvement.

The current diagnostic does not implement this new-data study. It prepares the comparison and identifies its remaining requirements. Model-by-effort data and measured overhead are still required for a confirmatory run.
