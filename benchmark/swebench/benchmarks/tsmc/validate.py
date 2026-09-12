"""Validate bundled baselines, reference fixes and mutants with the Docker harness."""

from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re

from swebench.benchmarks.tsmc import DATASET
from swebench.benchmarks.tsmc.grading.evaluator import RESULT_PREFIX
from swebench.benchmarks.tsmc.prepare import write_json
from swebench.harness.constants import RUN_EVALUATION_LOG_DIR
from swebench.harness.grading import get_eval_report
from swebench.harness.run_evaluation import (
    _docker_client,
    run_instance,
    write_run_metadata,
)
from swebench.harness.utils import make_test_spec
from swebench.task.publish import guard
from swebench.task.repo import load_task_repo


def read_result(log_path: Path) -> dict:
    lines = [
        line[len(RESULT_PREFIX) :]
        for line in log_path.read_text().splitlines()
        if line.startswith(RESULT_PREFIX)
    ]
    if len(lines) != 1:
        raise ValueError(f"Expected one canonical evaluator result in {log_path}")
    return json.loads(base64.b64decode(lines[0], validate=True))


def checked_images(client, instances):
    """Reject stale local tags before creating any trial artifacts."""
    images = {}
    for instance in instances:
        image = client.images.get(instance["image"])
        if image.labels.get("org.tsmc-bench.base-commit") != instance["base_commit"]:
            raise ValueError(
                f"Stale baseline in {instance['image']}; rebuild the task repo with "
                "swebench images build --force-rebuild -n swebench"
            )
        images[instance["instance_id"]] = image.id
    return images


def validate(
    task_repo: Path, run_id: str, tasks: list[str] | None = None, workers: int = 2
) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", run_id):
        raise ValueError("run_id must contain only letters, digits, _, . or -")
    if workers < 1:
        raise ValueError("workers must be positive")
    task_repo = task_repo.resolve()
    guard(task_repo)
    instances = load_task_repo(task_repo)
    if tasks:
        selected = {t.upper() for t in tasks}
        unknown = selected - {i["task_id"] for i in instances}
        if unknown:
            raise ValueError(f"Unknown task IDs: {sorted(unknown)}")
        instances = [i for i in instances if i["task_id"] in selected]
    run_dir = RUN_EVALUATION_LOG_DIR / run_id
    if run_dir.exists():
        raise ValueError(f"Use a fresh run_id; {run_dir} already exists")
    client = _docker_client()
    try:
        # Missing images fail before creating a partial validation run.
        images = checked_images(client, instances)
        splits = {instance["split"] for instance in instances}
        write_run_metadata(
            run_id,
            DATASET,
            next(iter(splits)) if len(splits) == 1 else "all",
            str(task_repo),
        )

        def run_task(instance):
            iid = instance["instance_id"]
            directory = task_repo / "tasks" / iid
            config = json.loads((directory / "tsmc.json").read_text())
            patches = {
                "baseline": "",
                "gold": instance["patch"],
                "gold_repeat": instance["patch"],
            }
            patches.update(
                {
                    name: (directory / "variants" / f"{name}.patch").read_text()
                    for name in config["variants"]
                }
            )
            spec = make_test_spec(instance)
            spec.image = images[iid]
            issues, results = [], {}
            for variant, patch in patches.items():
                prediction = dict(
                    instance_id=iid, model_patch=patch, model_name_or_path=variant
                )
                try:
                    evaluated = run_instance(
                        spec,
                        prediction,
                        client,
                        run_id,
                        timeout=config["test_timeout"] + 60,
                        skip_patch=not patch,
                        task_repo=str(task_repo),
                    )
                    if evaluated is None:
                        raise ValueError("Harness did not produce a report")
                    log_dir = run_dir / variant / iid
                    result = read_result(log_dir / "test_output.txt")
                    write_json(log_dir / "tsmc_result.json", result)
                    (log_dir / "pytest_output.txt").write_text(
                        result.get("raw_output", "")
                    )
                    regraded = get_eval_report(
                        spec, prediction, str(log_dir / "test_output.txt"), True
                    )
                    if regraded != evaluated[1]:
                        issues.append(
                            f"{variant}: regrading differs from original report"
                        )
                    expected_pass = variant.startswith("gold")
                    if (
                        result["resolved"] != expected_pass
                        or regraded[iid]["resolved"] != expected_pass
                    ):
                        issues.append(f"{variant}: incorrect resolution")
                    required = config["required"]
                    if set(result["collected"]) != set(required) or len(
                        result["collected"]
                    ) != len(required):
                        issues.append(f"{variant}: incorrect test collection")
                    statuses = {n: t["status"] for n, t in result["tests"].items()}
                    if result["timeout"] or any(
                        s not in {"passed", "failed"} for s in statuses.values()
                    ):
                        issues.append(f"{variant}: timeout or nonstandard test outcome")
                    if variant == "baseline":
                        for key, status in (
                            ("FAIL_TO_PASS", "failed"),
                            ("PASS_TO_PASS", "passed"),
                        ):
                            if any(statuses.get(n) != status for n in config[key]):
                                issues.append(f"baseline: {key} classification differs")
                    results[variant] = dict(
                        resolved=result["resolved"],
                        counts={
                            s: list(statuses.values()).count(s)
                            for s in ("passed", "failed")
                        },
                    )
                except (OSError, ValueError, KeyError) as exc:
                    issues.append(f"{variant}: {exc}")
            print(
                f"{instance['task_id']}: {'PASS' if not issues else 'FAIL'}", flush=True
            )
            return dict(
                task_id=instance["task_id"],
                instance_id=iid,
                image_id=images[iid],
                base_commit=instance["base_commit"],
                issues=issues,
                variants=results,
                original_test_count=len(config["required"]),
                gate_test_count=1,
            )

        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(run_task, instances))
        summary = dict(
            scope="docker-bundled-fixture-validation",
            run_id=run_id,
            all_qualified=bool(results) and not any(r["issues"] for r in results),
            tasks=results,
            original_test_count=sum(r["original_test_count"] for r in results),
            gate_test_count=len(results),
        )
        write_json(run_dir / "validation.json", summary)
        return summary
    finally:
        client.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--task-repo", type=Path, default=Path(".generated/tsmc/task-repo")
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--task", action="append")
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    result = validate(args.task_repo, args.run_id, args.task, args.workers)
    print(
        json.dumps(
            {"all_qualified": result["all_qualified"], "tasks": len(result["tasks"])}
        )
    )
    raise SystemExit(0 if result["all_qualified"] else 1)


if __name__ == "__main__":
    main()
