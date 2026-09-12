# IASES

**Importance-Aware Self-Evolving Scheduler for AI Agents**

Help AI agents decide **what matters, which tools run next, and which model to use**.

The demo simulates a wafer-fab incident competing with background tasks. It is inspired by TSMC operations, but is not affiliated with TSMC.

## Architecture

```mermaid
flowchart TB
    Human["Human preferences"] --> Evolver["Task Evolver"]
    Evolver --> Scores["Importance snapshot"]
    Scores --> Scheduler["Client Scheduler"]
    Agents["Codex sessions"] -->|"Tool calls"| Scheduler
    Scheduler -->|"Admission: importance + aging"| Tools["Tool execution slots"]
    Tools -->|"Results and slot release"| Agents

    Agents -->|"Model requests"| Gateway["Incident gateway"]
    Gateway -->|"Classify request"| Router["vLLM Semantic Router"]
    Router -->|"Semantic decision"| Gateway
    Scores -.->|"Optional importance policy"| Gateway
    Gateway -->|"Select backend"| Models["Low-cost or strong model"]
    Models -->|"Streamed response via gateway"| Agents
    HierShrink["HierShrink selector"] -.->|"Implemented, not enabled in live path"| Router

    subgraph Demo["Separate frontend demo"]
        Incident["Trigger incident"] --> Simulation["Mock queue and CPU / RAM display"]
    end
```

Solid arrows show implemented connections. Dashed arrows mark optional or inactive paths. The frontend remains separate; the full combined system has not passed an end-to-end test.

## Three main components

### 1. 🧠 Task Evolver: What matters?

- Learn task importance from human preference pairs.
- Convert preferences into scores with Bradley–Terry fitting.
- Publish updated scores for scheduling and routing policies.

<details>
<summary>How Task Evolver learns</summary>

```mermaid
flowchart TD
    Task["Task key"] --> Lookup{"Known importance?"}
    Lookup -->|"Yes"| Existing["Return current score"]
    Lookup -->|"No, learning enabled"| Human["Ask a human to compare two tasks"]
    Human --> Pair["Save preference pair in SQLite"]
    Pair --> Fit["Fit Bradley-Terry scores"]
    Fit --> Publish["Publish versioned importance snapshot: 0-100"]
    Fit --> Expand["Try LLM task expansion"]
    Expand -->|"New valid task variants"| Derived["Derive pairs from the human answer"]
    Derived --> Weight["Cap total expansion weight at 0.2 per parent pair"]
    Weight --> Refit["Refit scores"]
    Refit --> Publish
    Expand -->|"Failure or no new variants"| Keep["Keep scores from the human answer"]
    Publish --> Consumers["Scheduler and optional gateway policy"]
```

Human answers carry weight 1.0. LLM expansion adds low-weight derived pairs; it does not choose the human preference. Comparisons must connect to the reference task. Lookup without learning can return an unknown score instead of asking a question.

</details>

### 2. ⏱️ Client Scheduler: What runs next?

- Coordinate tool calls across multiple Codex sessions.
- Rank waiting tasks by importance and aging.
- Limit concurrent tool calls and release slots when calls finish.

### 3. 🔀 vLLM Semantic Router: Which model should respond?

- Classify requests, such as alert summaries or incident diagnosis.
- Route summaries to a low-cost model and diagnosis to a stronger model.
- Support HierShrink quality-cost selection through our custom selector, not yet enabled in the live gateway.

**Importance is not model difficulty.** Tool scheduling and model selection are separate decisions.

## 🚀 Try the demo

Use Node 22.18 or newer.

```sh
cd apps/demo
npm ci
npm run dev
```

Trigger an incident, switch scheduling policies, and compare the queue and resource display.

**Frontend only:** tasks, CPU, and RAM are simulated. The UI is not connected to the backend components.

## Current status

| Area | What works | What remains |
| --- | --- | --- |
| Evolver + Scheduler | Preference scores and cross-session tool admission | Full validation of newer pool and preemption changes |
| Semantic routing | A prior Codex → OpenAI tool round trip completed in 6.585 seconds | Combined frontend, scheduler, and HierShrink validation |
| HierShrink | Go selector, exporter, and tests | Live routing integration and evidence of quality-cost gains |

The first offline SWE pilot resolved 68/100 tasks, equal to fixed medium. It did not improve on that baseline. This is not a production deployment or a deadline guarantee.

## Development

<details>
<summary>Source layout</summary>

```text
apps/demo/                       Incident demo frontend
src/task-evolver/                Preference learning and shared admission
src/client-scheduler/            Codex scheduler crate
src/model-router/gateway/        Incident policy and Responses gateway
src/model-router/hiershrink/      Go model selector and tests
src/model-router/tools/          Exporter and offline pilot scripts
src/model-router/research/       Pilot's Python dependency subset
integrations/                    Pinned upstream revisions, patches, and adapters
scripts/prepare.py               Reconstruct the development workspace
```

Edit code in `src/`. Keep upstream wiring in `integrations/`.

Upstream sources, datasets, trained artifacts, credentials, caches, and binaries are not included. Patches modify existing upstream files. New adapter files live in `integrations/*/overlay/`. Licenses and notices remain under each integration.

</details>

<details>
<summary>Prepare the backend and run the routing smoke</summary>

Use Python 3.11 or newer and Git. The preparation command downloads the pinned upstream sources, applies patches, and copies our modules into their build locations.

```sh
python3 scripts/prepare.py
cd .work/codex
PYTHONPATH=tools/task-scheduler python3 -m unittest discover -s tools/task-scheduler/tests
```

Preparation requires a new destination. After source edits, use `--destination /path/to/new-workspace`. Do not edit the generated workspace as the source of record. All generated upstream files stay outside Git.

Build Codex and the native router libraries with their upstream build instructions in `.work/`. Set `OPENAI_API_KEY` in your environment or `.work/codex/.env`. Start the gateway from `.work/codex`:

```sh
PYTHONPATH=tools/task-scheduler python3 tools/semantic-router/run.py --router-root ../semantic-router
```

In another terminal, from `.work/codex`:

```sh
PYTHONPATH=tools/task-scheduler python3 tools/task-scheduler/experiments/semantic_router_probe.py --base-url http://127.0.0.1:18899/v1 --model incident-auto --output .cache/semantic-router/smoke.json
```

Use `--fast-model` and `--analysis-model` on the launcher to select model IDs available to your account. Keep the gateway on loopback; it has no client authentication.

</details>
