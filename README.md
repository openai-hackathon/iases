# IASES

**Importance-Aware Self-Evolving Scheduler for AI Agents**

TSMC-inspired incident recovery demo. This project is independent of TSMC.

## Layout

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

Edit code in `src/`. Keep upstream wiring in `integrations/`. The repository does not contain upstream source trees, datasets, credentials, caches, or binaries. Patches contain only changes to existing upstream files. New adapter files live in `integrations/*/overlay/`. Licenses and notices remain under each integration.

## Frontend

Use Node 22.18 or newer.

```sh
cd apps/demo
npm ci
npm test
npm run dev
```

The incident trigger, queue, CPU, and RAM display use simulated data. They do not control host resources.

## Backend workspace

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

## Status

- Evolver publishes Bradley–Terry importance from preference pairs.
- Scheduler implements cross-session admission, importance, aging, and tool lifecycle cleanup. New pool and preemption changes still need full integration validation.
- The prior local Codex to OpenAI Responses SSE smoke completed a tool round trip in 6.585 seconds. This was not a combined frontend, scheduler, and HierShrink test.
- HierShrink includes a Go selector, exporter, and tests. The live gateway does not enable it.
- The first offline SWE pilot resolved 68 of 100 tasks, equal to fixed medium. It did not show an improvement over that baseline. Pilot data and trained artifacts are not included.

Importance is not model difficulty. Tool scheduling and model selection remain separate decisions. This repository is not a production deployment or a deadline guarantee.
