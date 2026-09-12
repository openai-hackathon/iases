# TSMC-bench

A synthetic manufacturing software benchmark integrated with SWE-bench: 90 repair tasks (12 `demo_dev`, 23 `dev`, 55 reserved `test`) and four incident scenarios built from the original 12 tasks. The setting is an imagined semiconductor factory; the name implies no company affiliation or proprietary production data. `release.json` freezes the evaluation material. The [ten-task hard extension](../../docs/guides/tsmc_bench_hard_extension.md) preserves every original 80-task fixture and split. See the [scale and difficulty assessment](../../docs/guides/tsmc_bench_scale.md) and [dataset references](../../docs/guides/tsmc_bench_sources.md).

See the [TSMC-bench guide](../../docs/guides/tsmc_bench.md) for commands, API harness integration and validation.

The current release is `manufacturing-90-v4`. Its [hard-task reconstruction](../../docs/guides/tsmc_bench_hard_revision.md) substantially strengthens nine tasks and preserves A29, F25 and R29. Archived manifests and original replaced fixtures live in `releases/`.

| Directory | Purpose |
| --- | --- |
| `tasks/*/agent/` | Public requirements, baseline code, data and tests |
| `tasks/*/author/` | Reference patches, private required tests and mutants |
| `scenarios/public/` | Observable scenario, dependency graph and initial facts |
| `scenarios/author/` | Author-owned event traces and source mappings |
| `configs/agent.yaml` | Optional configuration for the existing mini-SWE-agent path |
| `configs/openai.yaml` | OpenAI provider overlay, applied after `configs/agent.yaml` |
| `configs/openai-luna.yaml` | GPT-5.6 Luna with medium reasoning, applied after the OpenAI overlay |
| `provenance.json` | Archive identity, original hashes and English edition hashes |

The original twelve tasks have behavior version `0.2`; expansion tasks use `1.0`, and explicitly revised tasks use `2.0`. Scenario semantics are version `0.3`. The original English edition translated requirements, contracts, notes and scenario descriptions while preserving implementation and test bytes. Later authored revisions have separate instance IDs and archived predecessors. Original archive hashes remain in provenance for comparison.

Maintain this source tree and regenerate `.generated/tsmc/` with `python -m swebench.benchmarks.tsmc.prepare`. Changes to public fixtures require corresponding updates to `task.json` hashes, test manifests, reference patches, mutants and provenance, followed by validation. Formatting hooks exclude task fixtures to preserve exact code and patch applicability.

The solver needs only the generated public dataset and public Docker image. Do not mount author directories, evaluation parquet or the complete SWE-bench checkout into its container.
