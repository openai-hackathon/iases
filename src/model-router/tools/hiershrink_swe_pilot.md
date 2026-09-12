# SWE-bench HierShrink pilot

Run from the semantic-router checkout. Reuse the CPU Python environment and training modules in the adjacent icr-router checkout. The task-scheduler module supplies the existing `.env` reader. No new packages are required in those environments.

```sh
PYTHONPATH=../icr-router/experiments:../codex/tools/task-scheduler OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4 CUDA_VISIBLE_DEVICES='' ../icr-router/.venv/bin/python tools/hiershrink_swe_pilot.py --output ../codex/.cache/hiershrink-swe-pilot --dotenv ../codex/.env
```

The completed output directory cannot be overwritten. Keep its original data, embeddings, protocol, profiles, and report. A new experiment needs a separate output directory. Interrupted runs after profile export can require a new directory because the exporter refuses to overwrite artifacts.

The input is the published SWE-bench team's mini-SWE-agent 1.17.2 results for GPT-5.2 medium and high. The collector pins the results repository revision. It retains only problem statements, identifiers, repositories, outcomes, costs, and call counts. Gold patches and hidden tests are not input features. Encoding uses OpenAI text-embedding-3-small with 1536 dimensions and the first 24,000 characters of each statement. Training uses the local CPU.

The fixed instance-level split has 150 construction, 150 profile, 100 validation, and 100 test instances. Both efforts for an instance stay together. Construction fits the existing LearnedMap and prompt geometry. The existing HierShrink fitter learns the profile on separate instances. Validation chooses shrinkage from 1, 5, 20, and 100 by Brier loss. It then chooses a cost weight by resolution rate within the declared validation budget. Test outcomes do not select parameters. The frozen fitter still uses its existing reference temperature and geometry assumptions; this is not an assumption-free estimator.

Each action identifies a whole-task model/effort setting. These aliases are profile columns, not deployed OpenAI model IDs. The trial does not estimate the result of switching effort midway through an agent trajectory. It does not use the importance threshold from the gateway.

## First trial

| Policy | Resolved / 100 | Historical cost, USD | High selections |
|---|---:|---:|---:|
| Learned policy | 68 | 26.19 | 0 |
| Fixed medium | 68 | 26.19 | 0 |
| Fixed high | 71 | 55.40 | 100 |

Validation selected shrinkage 100 and cost weight 0.5. The policy selected medium for every test instance. It did not improve over fixed medium. The paired resolution difference from the validation-selected best-quality fixed action, high, is -3 percentage points, with a percentile bootstrap interval of [-9, +3]. That comparator does not enforce the validation budget. These are replayed costs from published runs, not new inference spending.

This is one split and one observed run per action. It does not establish performance on unseen repositories or incidents. No production policy changed. The trained artifact is not connected to Codex or Client Scheduler.

## Replay

`profile.json` declares the actual encoder. `replay-profile.json` contains the same numeric arrays with the test-only encoder label expected by the existing Go replay harness. Replay uses saved embeddings and does not verify a live encoder connection.

From `src/semantic-router`, use the existing native library environment and run:

```sh
HIERSHRINK_REPLAY=/absolute/path/to/output/replay.json go test -tags=milvus ./pkg/selection -run HierShrink -count=1 -v
```

The replay checks both action utilities and the selected action for all 100 test embeddings. It does not launch OpenAI inference or the scheduler.
