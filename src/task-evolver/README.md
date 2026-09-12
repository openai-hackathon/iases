# Task evolver

Run commands from the repository root with Python 3.11 or newer.
Set `OPENAI_API_KEY` in your environment or the repository root `.env`.
Environment variables take precedence over `.env`. The file also supports
`TASK_EVOLVER_MODEL`, quoted values, and `export` prefixes.
Set `TASK_EVOLVER_MODEL` to your OpenAI model ID, or pass `--model MODEL`.
Use a model that supports Responses API structured outputs.
Set `TASK_EVOLVER_REASONING_EFFORT=medium` for medium reasoning effort.
If unset, the request omits `reasoning`.
The local `.env` uses `TASK_EVOLVER_MODEL=gpt-5.6-luna` and medium effort.

Compare two tasks with a human preference score:

```sh
PYTHONPATH=tools/task-scheduler python3 -m task_evolver --db task-evolver.sqlite3 --reference "開源維護" compare "生產事故處理" "開源維護" --score 0.7
```

The score expresses preference for the first task over the second task.
Use 1 for the first task, 0 for the second task, or 0.5 for equal importance.
Intermediate values are valid. Omit `--score` to enter a number at the prompt.
Repeat a comparison to correct an earlier answer.

The first comparison must contain the reference task.
Keep the same reference for the database.
Each later comparison must connect to the existing reference group.

The command saves the human answer and updates the scores first.
It then calls the OpenAI Responses API to expand each task and updates the scores again.
The model receives task descriptions without preference scores.
The command removes duplicate and existing keys.
Each parent comparison has a total expansion weight of at most 0.2.

Use `--model MODEL` before `compare` to select the expansion model.
Expansion sends only task descriptions to `https://api.openai.com/v1/responses`.
It requests JSON schema output and sets `store=false`.
It uses API credentials, not Codex CLI login. No tool definitions are sent.
Each model call has a 60-second timeout.

If expansion fails, the JSON result contains `expansion_error`.
The saved human answer and the last valid score table remain available.
If fitting fails, the command reports an error and keeps the last score table.
The human answer stays saved for a later refit.

Look up a score without asking a human:

```sh
PYTHONPATH=tools/task-scheduler python3 -m task_evolver --db task-evolver.sqlite3 --reference "開源維護" lookup "生產事故處理" --no-ask
```

With `--no-ask`, a missing key keeps `importance: null`. An enabled embedding model can still return candidates. Without this flag, lookup asks for
a 0–1 comparison against the fixed reference, saves the answer, expands it, and
refits. A known key does not ask or call the model.
Use `init KEYWORD ...` to initialize a connected comparison set. Each unique new
keyword is compared with the reference; the reference itself needs no answer.
Importance uses the 0–100 scale. Human input uses the separate 0–1 pair scale.
Run one evolver writer at a time. Use the shared service below for cross-process admission.

Run the tests:

```sh
PYTHONPATH=tools/task-scheduler python3 -m unittest discover -s tools/task-scheduler/tests -v
```

## Connect the local Rust scheduler

Publish scores after each human answer and each expansion refit:

```sh
PYTHONPATH=tools/task-scheduler python3 -m task_evolver \
  --db task-evolver.sqlite3 --reference "開源維護" \
  --snapshot "$PWD/importance.json" \
  --bind /absolute/path/to/incident-repo "生產事故處理" \
  --bind /absolute/path/to/oss-repo "開源維護" \
  compare "生產事故處理" "開源維護" --score 0.7
```

Set these variables on the app-server process built from this checkout:

```sh
export CODEX_SCHEDULER_IMPORTANCE="$PWD/importance.json"
export CODEX_SCHEDULER_RATE=1
export CODEX_SCHEDULER_SLOTS=1
```

The importance file selects the learned policy instead of the tier policy.
Use the same snapshot path and full binding list for each comparison.
To publish existing scores without a model call, replace `compare ... --score ...`
with `export` and keep the other arguments.

The scheduler reloads the snapshot before each queue selection.
It uses `importance + waiting_seconds * rate`. A zero rate disables aging.
An invalid rate uses 1 point per second and emits a warning.
The most specific matching directory selects the task key.
A directory without a binding, or a key without a score, uses 50 points plus aging.
Bindings are explicit task context labels. The scheduler does not infer importance
from a repository name, or distinguish two task contexts in the same directory.

A malformed or missing snapshot keeps the last valid scores.
An older fit version cannot replace a newer one.
Keep the same database for a running scheduler. Restart it if the database is reset.
Score updates do not reset waiting time or interrupt running tools.
Snapshot files have a 1 MiB limit.

SQLite commits before snapshot publication. If publication fails, the database
can have newer scores than the file. Correct the file error and run `export` again.
The snapshot must use a different path from the database.

This connection shares scores across processes. Each process still owns its queue
and slot limit. Use the shared service below to centralize admission.


## Shared admission service

Start one service:

```sh
PYTHONPATH=tools/task-scheduler python3 -m task_evolver.admission \
  --port 8765 --slots 1 --rate 1 --snapshot "$PWD/importance.json"
```

Set this variable on each app-server process built from this checkout:

```sh
export CODEX_SCHEDULER_SERVICE=127.0.0.1:8765
```

An invalid or non-loopback service address disables the scheduler with a warning.
Service mode overrides local admission. The service owns the queue, slot count,
arrival times, snapshot and aging rate. Local `SLOTS`, `RATE`, and `IMPORTANCE`
settings do not control the shared queue.

The transport uses localhost TCP with one JSON message per line.
Each connection owns one tool call. Enqueue fields are `op=enqueue`, `client_id`,
`thread_id`, `turn_id`, `call_id`, `cwd`, and `tool`.
The service sends `status=queued`, then `status=granted` when a slot is available.
It accepts `op=release` or `op=cancel`. Both return `status=released`.
The Rust adapter closes the connection to release or cancel its call.
Disconnect removes that connection's call and grants the next waiter.

Repeating enqueue on the same connection returns its current status without a
second slot. Repeating release or cancel has no extra effect. A second connection
with an active duplicate identity is rejected. Reconnect and durable retry are
not implemented. Rust uses a unique client identity for each process instance.
The service keeps at most 4096 active calls. Each input line has a 64 KiB limit.

If connection or admission fails, the Rust gate remains blocked until the host
cancels it. Service mode does not use the local 300-second fail-open path.
Restore the service and cancel or retry the affected turn.

A slot is a connection lease, not control over an operating-system process.
Disconnect releases the lease but cannot stop a tool that already started.
Stop client work before restarting the service. There is no crash recovery or
lease reconciliation across service restarts. Queues are held in memory.
Use `--trace PATH` on the service for remote enqueue, grant, release, cancel and
disconnect events. Trace write errors warn without blocking admission. Rust
closes its lease on completion and cancellation, so a disconnect event alone
does not prove successful tool completion. Cross-check app-server turn outcomes.

See the [OpenAI structured output format](https://developers.openai.com/api/docs/guides/structured-outputs)
for the expansion request contract.


## Automatic questions in the service

Publish an initial snapshot with all working-directory bindings. Empty scores are valid:

```sh
PYTHONPATH=tools/task-scheduler python3 -m task_evolver \
  --db task-evolver.sqlite3 --reference "開源維護" \
  --snapshot "$PWD/importance.json" \
  --bind /absolute/path/to/incident-repo "生產事故處理" \
  --bind /absolute/path/to/oss-repo "開源維護" export

PYTHONPATH=tools/task-scheduler python3 -m task_evolver.admission \
  --snapshot "$PWD/importance.json" --db task-evolver.sqlite3 \
  --reference "開源維護" --slots 1 --rate 1 --trace scheduler.jsonl
```

Keep the service terminal open. Unknown bound keys and uncertain waiting pairs can trigger a question there.
Each key has at most one pending question. Unknown keys use 50 points plus
aging without writing that fallback to the score table. Known keys retain their fitted scores. Tools can run before the
answer arrives; questions do not stop admission. Directories without a binding
use fallback without a question. Directory matching resolves symlinks.

The worker saves each human answer, runs OpenAI expansion, and publishes scores.
Only the worker writes the database while interactive service learning is active.
To correct an existing pair through `compare`, first stop the learning service
and client work. Restart after the correction. EOF stops automatic questions;
admission continues with the current scores. Restart the service to resume questions.
Service restarts and crash recovery remain outside this demo's scope.

See [the demo and experiment guide](DEMO.md) for reproducible verification.

## Embedding candidates

Set `TASK_EVOLVER_EMBEDDING_MODEL=text-embedding-3-small` in the environment or
repository root `.env` before restarting the learning service. Leave it unset
to disable semantic requests. This setting is separate from the expansion model.
The adapter uses the [OpenAI embeddings API](https://developers.openai.com/api/reference/resources/embeddings/methods/create).
It sends normalized task descriptions and requests 256-dimensional float vectors.
It uses the same `OPENAI_API_KEY`, a 15-second timeout, and a 2 MiB response cap.

For a CLI lookup, select the embedding model explicitly:

```sh
PYTHONPATH=tools/task-scheduler python3 -m task_evolver \
  --db task-evolver.sqlite3 --reference "開源維護" \
  --embedding-model text-embedding-3-small lookup "線上付款服務無法使用" --no-ask
```

`lookup.source` distinguishes human, seed, expanded, reference, embedding, and miss.
An exact score takes precedence and skips the embedding API.
On a miss, the result includes up to three positive-cosine candidates with their
scores and evidence sources. `estimated_importance` is their cosine-weighted mean.
This estimate is advisory. It never enters the BT score table or creates a pair.
The scheduler keeps its existing fallback until a human answer produces a fitted score.
Similarity does not establish matching incident status or urgency.

The lookup examines at most 128 fitted keys in key order. This is a bounded demo
index, not a nearest-neighbor search over all keys in a larger database.
SQLite caches at most 4096 vectors, with separate entries for each model and key.
A failed embedding request returns `embedding_error` and preserves learned scores.
`--no-ask` can write this cache, but it does not write preference pairs.

## Active questions

The service sends a snapshot of up to 64 waiting task keys to its learning worker.
The worker ranks candidate comparisons by evidence uncertainty and queue impact.
Pairs with both tasks waiting get more weight; close current scheduling scores
increase the impact. Unknown or expanded-only keys get higher uncertainty than
human-backed keys. A human-backed pair can return for review when its preference
differs from the fitted BT probability by at least 0.25.
These weights and the 0.25 cutoff are heuristics, not calibrated confidence levels.

The comparator must already have a fitted score. If no waiting comparator qualifies,
the worker uses the fixed reference. This rule keeps the comparison graph connected.
Before asking, the worker shows the selection reason and any embedding candidates.
It rechecks the queue after embedding I/O and drops canceled waiting questions.
An already displayed question remains active until the user answers or sends EOF.

The service asks one question at a time, deduplicates pending keys, and applies a
60-second cooldown to each unordered pair. Each service process allows at most
10 questions, including failed or abandoned attempts. This is a service-wide limit,
not a per-client budget. Admission continues after the limit; restart to reset it.
Human answers remain 0–1 preferences and use the existing override and refit path.
