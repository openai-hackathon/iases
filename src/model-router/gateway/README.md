# Incident semantic routing

Run these commands from the repository root. Use Python 3.11+, Go, and a built native [vLLM Semantic Router](https://github.com/vllm-project/semantic-router/tree/a08a982388f83d4daabb3e6a3c40240bd0a96238) checkout at the pinned commit. Its `candle-binding`, `ml-binding`, and `nlp-binding` release libraries must exist. This setup was tested on macOS arm64. The launcher builds the Go router; `--binary` can select an existing compatible build.

1. Set `OPENAI_API_KEY` in the environment or the repository `.env`.
2. Start the router and local gateway:

   ```sh
   PYTHONPATH=tools/task-scheduler python3 tools/semantic-router/run.py --router-root ../semantic-router
   ```

3. Verify a real Codex tool round trip in another terminal:

   ```sh
   PYTHONPATH=tools/task-scheduler python3 tools/task-scheduler/experiments/semantic_router_probe.py --base-url http://127.0.0.1:18899/v1 --model incident-auto --output .cache/semantic-router/codex-probe.json
   ```

The probe needs `codex-rs/target/debug/codex`, or `--binary PATH`. It uses a temporary Codex home, runs one harmless shell command, and requires both successful tool output and the final model confirmation. Stop the launcher with Ctrl-C. Logs and generated configuration stay under `.cache/semantic-router`.

Codex sends Responses requests to the gateway. The gateway sends the latest user text to the official router's `/api/v1/classify/intent` endpoint. OpenAI `text-embedding-3-small` supplies embeddings. Summary requests select `incident-fast` (`gpt-5.6-luna`). Diagnosis and uncertain requests select `incident-analysis` (`gpt-5.6-sol`). Override backend IDs with `--fast-model` and `--analysis-model`.

The gateway changes only `model` in the JSON payload and streams upstream SSE bytes. This preserves Codex tools and encrypted reasoning that the pinned router's native Responses codec does not fully support. Response headers expose `x-vsr-selected-model`, `x-vsr-selected-decision`, and `x-incident-upstream-model`. Classification failure returns 503 without an inference call.

This is a local semantic-routing MVP with real OpenAI inference. It does not implement GPU scheduling, load-aware instance selection, or deadline guarantees. Task Evolver and Client Scheduler remain separate components. The probe isolates routing and does not test their combined scheduling behavior.

Send full input history with `model: incident-auto`; server-stored `previous_response_id` is unsupported. Each request is classified again. The gateway accepts at most 8 MiB per request and 16,384 characters in the latest user text. The local gateway binds to loopback and has no client authentication. Do not expose it as a public service.

Run regression tests with `PYTHONPATH=tools/task-scheduler python3 -m unittest discover -s tools/task-scheduler/tests`. HTTP integration tests cover payload preservation, incremental SSE, semantic failures, and request validation. Routing thresholds are initial settings, not an accuracy benchmark.

## Fuse task importance

Use the same published snapshot as Client Scheduler:

```sh
PYTHONPATH=tools/task-scheduler python3 tools/semantic-router/run.py --router-root ../semantic-router --importance-snapshot /path/to/importance.json
```

Add this field inside your Codex `[model_providers.semantic_router]` configuration and set `INCIDENT_TASK_KEY` to the matching snapshot key before starting Codex:

```toml
env_http_headers = { "X-Incident-Task-Key" = "INCIDENT_TASK_KEY" }
```

The header contains a task key, never a trusted numeric score. Percent-encode UTF-8 keys that contain non-ASCII text or `%`. The probe's `--task-key KEY` option does this automatically. The gateway reads the score locally and does not forward this header to OpenAI.

Fusion rule: `analysis` if the semantic route selects analysis **or** task importance is at least 80; otherwise retain the semantic route. Set `--importance-threshold` to change this initial policy. Missing keys retain semantic routing. Low scores never demote diagnosis requests. This threshold is a policy choice, not a measured quality or latency guarantee.

Scores describe task importance; tools inherit the score of their task. They do not measure model difficulty or individual tool quality. The gateway refreshes the snapshot per request and keeps the last valid version on corrupt or older updates, as Client Scheduler does. An invalid initial snapshot prevents startup. It does not combine importance numerically with embedding similarity because the two scores have different meanings.

`x-vsr-selected-model` retains the original semantic choice. `x-incident-selected-model` reports the final choice; `x-incident-routing-reason`, `x-incident-importance`, and `x-incident-fit-version` explain the importance signal. The JSON body still changes only at `model`.
