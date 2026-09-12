"""Run a fixed development-task matrix with resumable, independently graded trials."""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
import csv
from datetime import datetime, timezone
import hashlib
import fcntl
import json
from pathlib import Path
import random
import re
import subprocess
import threading
import time

from swebench.benchmarks.tsmc import timing
from swebench.inference.workspace_agent import atomic_write_json
from swebench.task.repo import dump_yaml, load_task_repo


TASK_IDS = ("A05", "F05", "R05", "A12", "F11", "R13", "R21", "A29", "F25", "R29")
EFFORTS = ("none", "low", "medium", "high", "xhigh", "max")
PRICING = {
    "gpt-5.6-sol": {
        "input": 4.0,
        "cached_input": 0.4,
        "cache_write": 5.0,
        "output": 20.0,
    },
    "gpt-5.6-terra": {
        "input": 2.0,
        "cached_input": 0.2,
        "cache_write": 2.5,
        "output": 12.0,
    },
    "gpt-5.6-luna": {
        "input": 0.2,
        "cached_input": 0.02,
        "cache_write": 0.25,
        "output": 1.2,
    },
    "gpt-6-astra": {
        "input": 10.0,
        "cached_input": 1.0,
        "cache_write": 12.5,
        "output": 50.0,
    },
}
PUBLIC_COLUMNS = {
    "instance_id",
    "repo",
    "version",
    "base_commit",
    "task_id",
    "image_name",
    "problem_statement",
}


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    return json.loads(Path(path).read_text())


def read_partial_json(path):
    """Read best-effort evidence while reporting a failed or interrupted trial."""
    try:
        value = read_json(path)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@contextmanager
def experiment_lock(output):
    """Prevent overlapping drivers from charging for the same scheduled trial."""
    with (output / ".driver.lock").open("a+") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError(
                "Another driver is already running this experiment"
            ) from exc
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def conditions():
    """The Sol alias is deliberately excluded: these are 23 distinct settings."""
    return [
        {"condition_id": f"{model}__{effort}", "model": model, "effort": effort}
        for model in PRICING
        for effort in EFFORTS
        if model != "gpt-6-astra" or effort != "none"
    ]


def select_tasks(rows, release):
    if len({row["task_id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate public task identifiers")
    by_id = {row["task_id"]: row for row in rows}
    metadata = {row["task_id"]: row for row in release["tasks"]}
    selected, tasks = [], []
    for task_id in TASK_IDS:
        row, meta = by_id[task_id], metadata[task_id]
        if set(row) != PUBLIC_COLUMNS:
            raise ValueError(
                "Solver dataset must contain only the seven public columns"
            )
        if meta["split"] != "dev" or row["instance_id"] != meta["instance_id"]:
            raise ValueError(f"Task is outside the frozen development split: {task_id}")
        selected.append(dict(row))
        tasks.append(
            {
                "task_id": task_id,
                "instance_id": row["instance_id"],
                "difficulty": meta["design_difficulty"],
                "family": meta["family"],
                "split": "dev",
                "base_commit": row["base_commit"],
                "required_test_count": meta["required_tests"],
            }
        )
    if Counter(t["difficulty"] for t in tasks) != {"easy": 3, "medium": 4, "hard": 3}:
        raise ValueError(
            "Expected exactly three easy, four medium and three hard tasks"
        )
    return selected, tasks


def condition_config(condition, *, steps=50, timeout=600):
    config = timing.prepare_config(
        [
            Path("benchmarks/tsmc/configs/agent.yaml"),
            Path("benchmarks/tsmc/configs/openai-responses.yaml"),
        ],
        steps=steps,
        timeout=timeout,
    )
    config["agent"]["cost_limit"] = 0
    config["model"].update(
        model_name=f"openai/{condition['model']}",
        pricing_per_million=PRICING[condition["model"]],
    )
    config["model"]["model_kwargs"].update(
        reasoning={"effort": condition["effort"]},
        max_output_tokens=32768,
        timeout=timeout,
        num_retries=0,
        service_tier="default",
    )
    return config


def prepare(
    output,
    dataset,
    task_repo,
    *,
    run_id,
    workers=6,
    steps=50,
    timeout=600,
    seed=20260912,
):
    """Freeze public inputs, immutable image identities and all condition settings."""
    import docker
    import pyarrow as pa
    import pyarrow.parquet as pq
    from swebench.benchmarks.tsmc.release import verify_release
    from swebench.benchmarks.tsmc.validate import checked_images

    if output.exists():
        raise ValueError(
            "Use --resume for an existing experiment; paid trials are never overwritten"
        )
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", run_id):
        raise ValueError("Invalid experiment run ID")
    if min(workers, steps, timeout) <= 0:
        raise ValueError("Workers and budgets must be positive")
    timing.check_disk_space(output, 1024**3)
    source = Path("benchmarks/tsmc").resolve()
    verify_release(source)
    release = read_json(source / "release.json")
    rows, tasks = select_tasks(
        pq.read_table(dataset / "dev.parquet").to_pylist(), release
    )
    smoke_row = next(
        r
        for r in pq.read_table(dataset / "demo_dev.parquet").to_pylist()
        if r["task_id"] == "F01"
    )
    smoke_meta = next(r for r in release["tasks"] if r["task_id"] == "F01")
    smoke_task = {
        "task_id": "F01",
        "instance_id": smoke_row["instance_id"],
        "difficulty": smoke_meta["design_difficulty"],
        "split": "demo_dev",
        "base_commit": smoke_row["base_commit"],
        "required_test_count": smoke_meta["required_tests"],
    }
    if (
        set(smoke_row) != PUBLIC_COLUMNS
        or smoke_task["instance_id"] != smoke_meta["instance_id"]
    ):
        raise ValueError("Invalid public smoke task")
    instances = load_task_repo(
        task_repo, [t["instance_id"] for t in [*tasks, smoke_task]]
    )
    by_iid = {i["instance_id"]: i for i in instances}
    for row in [*rows, smoke_row]:
        instance = by_iid[row["instance_id"]]
        for field in PUBLIC_COLUMNS:
            if row[field] != instance["image" if field == "image_name" else field]:
                raise ValueError(
                    f"Public and evaluator task inputs differ: {row['instance_id']} {field}"
                )
    client = docker.from_env(timeout=30)
    try:
        images = checked_images(client, instances)
    finally:
        client.close()
    for row, task in zip([*rows, smoke_row], [*tasks, smoke_task], strict=True):
        row["image_name"] = task["image_id"] = images[row["instance_id"]]
    configs = {
        c["condition_id"]: condition_config(c, steps=steps, timeout=timeout)
        for c in conditions()
    }
    output.mkdir(parents=True)
    public = output / "public"
    public.mkdir()
    pq.write_table(pa.Table.from_pylist(rows), public / "dev.parquet")
    (public / "README.md").write_text(
        "---\n"
        + dump_yaml(
            {
                "configs": [
                    {
                        "config_name": run_id,
                        "data_files": [{"split": "dev", "path": "dev.parquet"}],
                    }
                ]
            }
        )
        + "---\nFixed public development sample for the model and effort experiment.\n"
    )
    smoke_public = output / "smoke-public"
    smoke_public.mkdir()
    pq.write_table(pa.Table.from_pylist([smoke_row]), smoke_public / "dev.parquet")
    (smoke_public / "README.md").write_text(
        "---\n"
        + dump_yaml(
            {
                "configs": [
                    {
                        "config_name": run_id + "-smoke",
                        "data_files": [{"split": "dev", "path": "dev.parquet"}],
                    }
                ]
            }
        )
        + "---\nUnscored F01 smoke task. Original benchmark split: demo_dev.\n"
    )
    source_files = [
        "swebench/benchmarks/tsmc/experiment.py",
        "swebench/benchmarks/tsmc/experiment_report.py",
        "swebench/benchmarks/tsmc/timing.py",
        "swebench/inference/openai_responses.py",
        "swebench/inference/workspace_agent.py",
        "benchmarks/tsmc/configs/agent.yaml",
        "benchmarks/tsmc/configs/openai-responses.yaml",
    ]
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "created_at": now(),
        "release": release["release"],
        "release_content_sha256": release["content_sha256"],
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "source_sha256": {p: sha256(p) for p in source_files},
        "dataset_source": str(dataset.resolve()),
        "task_repo": str(task_repo.resolve()),
        "public_sha256": sha256(public / "dev.parquet"),
        "smoke_public_sha256": sha256(smoke_public / "dev.parquet"),
        "smoke_task": smoke_task,
        "smoke_policy": "One full F01 smoke per condition before its ten scored trials; separate costs and scores; require complete telemetry and a native grading result",
        "tasks": tasks,
        "conditions": conditions(),
        "configs": configs,
        "workers": workers,
        "step_limit": steps,
        "hard_timeout_seconds": timeout,
        "max_output_tokens_per_request": 32768,
        "per_task_cost_limit_usd": None,
        "request_retries": 0,
        "agent_query_retries": 0,
        "schedule_seed": seed,
        "expected_trials": len(tasks) * len(conditions()),
        "expected_smoke_trials": len(conditions()),
        "expected_total_trials": (len(tasks) + 1) * len(conditions()),
        "pricing": {
            "source": "https://developers.openai.com/api/docs/pricing",
            "verified_on": "2026-09-12",
            "currency": "USD",
            "service_tier": "default",
            "rates_per_million_tokens": PRICING,
            "long_context_threshold": 272000,
            "long_context_input_multiplier": 2,
            "long_context_output_multiplier": 1.5,
            "scope": "Usage-based estimates, not an invoice; interrupted requests may have unreported billable usage",
        },
        "methodology": {
            "selection": "Fixed representative development tasks selected before model execution",
            "difficulty": "Author estimates; this sample is not an estimate of full-benchmark accuracy",
            "repetitions_per_condition_task": 1,
            "api": "https://api.openai.com/v1/responses",
            "solver_input": "Public issue, baseline source and public tests only",
            "grading": "Fresh native SWE-bench containers with the original hidden and public TSMC tests",
            "inference_time": "Subprocess and container startup plus solving, before owned-container cleanup",
            "total_trial_time": "Solving and cleanup plus grading; queue wait is recorded separately",
            "accuracy": "Resolved tasks divided by all ten requested tasks; infrastructure failures remain separately classified",
            "cache": "Natural API caching; observed cache reads and writes are recorded per response",
        },
    }
    atomic_write_json(output / "manifest.json", manifest)
    refresh_reports(output, manifest)
    return manifest


def verify_resume(output):
    manifest = read_json(output / "manifest.json")
    if sha256(output / "public/dev.parquet") != manifest["public_sha256"]:
        raise ValueError("Frozen public dataset changed")
    if sha256(output / "smoke-public/dev.parquet") != manifest["smoke_public_sha256"]:
        raise ValueError("Frozen smoke dataset changed")
    for path, expected in manifest["source_sha256"].items():
        if sha256(path) != expected:
            raise ValueError(
                f"Experiment implementation changed; do not mix protocols: {path}"
            )
    release = read_json("benchmarks/tsmc/release.json")
    if release["content_sha256"] != manifest["release_content_sha256"]:
        raise ValueError("Benchmark release changed")
    return manifest


def trial_directory(output, condition, task, *, smoke=False):
    return (
        output
        / ("smokes" if smoke else "trials")
        / condition["condition_id"]
        / task["instance_id"]
    )


def grade_trial(instance, prediction, *, task_repo, run_id, condition_id, image_id):
    """Grade the collected patch in a fresh container and preserve canonical evidence."""
    import docker
    from swebench.benchmarks.tsmc.validate import read_result
    from swebench.harness.constants import APPLY_PATCH_FAIL, RUN_EVALUATION_LOG_DIR
    from swebench.harness.run_evaluation import run_instance
    from swebench.harness.utils import make_test_spec

    start = time.perf_counter()
    iid = instance["instance_id"]
    patch = prediction.get("model_patch") or ""
    result = {
        "status": "empty_submission",
        "resolved": False,
        "patch_applied": False,
        "grading_seconds": 0.0,
        "patch_sha256": hashlib.sha256(patch.encode()).hexdigest(),
    }
    if not patch.strip():
        return result
    prediction = {**prediction, "model_name_or_path": condition_id}
    spec = make_test_spec(instance)
    spec.image = image_id
    log_dir = RUN_EVALUATION_LOG_DIR / run_id / condition_id / iid
    existing_report = log_dir / "report.json"
    if existing_report.exists() and (
        not (log_dir / "patch.diff").exists()
        or (log_dir / "patch.diff").read_text() != patch
    ):
        raise ValueError("Existing grading evidence belongs to a different patch")
    client = docker.from_env(timeout=90)
    try:
        report = run_instance(
            spec, prediction, client, run_id, timeout=180, task_repo=str(task_repo)
        )
        result["log_directory"] = str(log_dir.resolve())
        if report is None:
            log_path = log_dir / "run_instance.log"
            logs = log_path.read_text() if log_path.exists() else ""
            result.update(
                status="patch_failure" if APPLY_PATCH_FAIL in logs else "grading_error",
                resolved=False if APPLY_PATCH_FAIL in logs else None,
            )
            return result
        native = report[1][iid]
        result.update(
            status="infrastructure_failure"
            if native.get("infra_failure")
            else "graded",
            resolved=None if native.get("infra_failure") else bool(native["resolved"]),
            patch_applied=native.get("patch_successfully_applied"),
        )
        canonical = read_result(log_dir / "test_output.txt")
        if canonical.get("patch_sha256") != hashlib.sha256(patch.encode()).hexdigest():
            raise ValueError("Native evaluator graded a different patch")
        atomic_write_json(log_dir / "tsmc_result.json", canonical)
        statuses = [t["status"] for t in canonical.get("tests", {}).values()]
        required = [
            n
            for n in spec.FAIL_TO_PASS + spec.PASS_TO_PASS
            if n != "tsmc_grader::required_suite"
        ]
        result.update(
            tests_passed=statuses.count("passed"),
            tests_failed=statuses.count("failed"),
            tests_total=len(required),
            hidden_tests_passed=sum(
                t["status"] == "passed"
                for n, t in canonical.get("tests", {}).items()
                if n.startswith("assessment/")
            ),
            hidden_tests_total=sum(n.startswith("assessment/") for n in required),
            required_suite_passed=bool(canonical["resolved"]),
            evaluator_seconds=canonical.get("seconds"),
        )
        if (
            result["resolved"] is not None
            and result["resolved"] != canonical["resolved"]
        ):
            raise ValueError("Native report and canonical evaluator disagree")
    except Exception as exc:
        result.update(
            status="grading_error", resolved=None, error=f"{type(exc).__name__}: {exc}"
        )
    finally:
        client.close()
        result["grading_seconds"] = time.perf_counter() - start
    return result


def read_events(path):
    if not path.exists():
        return None
    events = []
    for index, line in enumerate(path.read_text().splitlines()):
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            events.append({"event": "invalid_journal_record", "line": index + 1})
    return events


def execute_trial(
    output, manifest, condition, task, row, instance, grade_lock, *, smoke=False
):
    from swebench.benchmarks.tsmc.experiment_report import summarize_trial

    directory = trial_directory(output, condition, task, smoke=smoke)
    result_path = directory / "result.json"
    if result_path.exists():
        return read_json(result_path)
    journal = directory / "requests.jsonl"
    started = time.perf_counter()
    if directory.exists():
        if not (directory / "timing.json").exists():
            raise ValueError(
                f"Interrupted trial has no final timing artifact; it will not be silently rerun: {directory}"
            )
        measured = read_json(directory / "timing.json")
    else:
        measured = timing.run_instance(
            row,
            directory,
            manifest["configs"][condition["condition_id"]],
            output / ("smoke-public" if smoke else "public"),
            "dev",
            manifest["hard_timeout_seconds"],
            retry_attempts=1,
            request_log_path=journal,
        )
    iid = task["instance_id"]
    trajectory_path = directory / "inference" / iid / f"{iid}.traj.json"
    prediction_path = directory / "inference/preds.json"
    trajectory = read_json(trajectory_path) if trajectory_path.exists() else {}
    prediction = (
        read_json(prediction_path).get(iid, {}) if prediction_path.exists() else {}
    )
    submitted = trajectory.get("info", {}).get("submission") or ""
    patch = prediction.get("model_patch") or ""
    evaluation_path = directory / "evaluation.json"
    grade_queued = time.perf_counter()
    if evaluation_path.exists():
        evaluation = read_json(evaluation_path)
        if evaluation.get("patch_sha256") != hashlib.sha256(patch.encode()).hexdigest():
            raise ValueError("Saved grading result belongs to a different patch")
    elif submitted != patch:
        evaluation = {
            "status": "submission_mismatch",
            "resolved": None,
            "grading_seconds": 0.0,
        }
    else:
        with grade_lock:
            grade_queue_seconds = time.perf_counter() - grade_queued
            evaluation = grade_trial(
                instance,
                prediction,
                task_repo=manifest["task_repo"],
                run_id=f"{manifest['run_id']}{'-smoke' if smoke else ''}-{condition['condition_id']}",
                condition_id=condition["condition_id"],
                image_id=task["image_id"],
            )
        evaluation["grade_queue_seconds"] = grade_queue_seconds
    atomic_write_json(evaluation_path, evaluation)
    result = summarize_trial(
        iid,
        timing=measured,
        trajectory=trajectory,
        evaluation=evaluation,
        request_events=read_events(journal),
    )
    result.update(
        task_id=task["task_id"],
        difficulty=task["difficulty"],
        state="completed",
        model=condition["model"],
        effort=condition["effort"],
        phase="smoke" if smoke else "scored",
        patch_bytes=len(patch.encode()),
        patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),
        submission_source=trajectory.get("info", {}).get("submission_source"),
        trial_directory=str(directory.resolve()),
        evaluation=evaluation,
        trial_wall_seconds=time.perf_counter() - started,
    )
    atomic_write_json(result_path, result)
    return result


def smoke_issues(result):
    issues = []
    if not result.get("usage_complete"):
        issues.append("Token accounting is incomplete")
    if not result.get("cost_estimate_complete"):
        issues.append("Cost accounting is incomplete")
    if not result.get("response_count"):
        issues.append("No model response was recorded")
    if result.get("evaluation_status") != "graded" or not isinstance(
        result.get("resolved"), bool
    ):
        issues.append("No native grading result for the submitted patch")
    if not result.get("patch_bytes"):
        issues.append("No workspace patch was collected")
    for field in ("inference_seconds", "grading_seconds", "total_seconds"):
        if not isinstance(result.get(field), (int, float)):
            issues.append(f"Missing timing: {field}")
    return issues


def refresh_reports(output, manifest):
    """Keep one atomic JSON per condition and an experiment-wide JSON/CSV index."""
    from swebench.benchmarks.tsmc.experiment_report import summarize_condition

    directory = output / "conditions"
    directory.mkdir(exist_ok=True)
    summaries, all_trials, all_smokes = [], [], []
    for condition in manifest["conditions"]:
        records = []
        for task in manifest["tasks"]:
            path = trial_directory(output, condition, task) / "result.json"
            records.append(
                read_json(path)
                if path.exists()
                else {
                    "instance_id": task["instance_id"],
                    "task_id": task["task_id"],
                    "difficulty": task["difficulty"],
                    "model": condition["model"],
                    "effort": condition["effort"],
                    "state": "pending",
                    "inference_status": "Pending",
                    "evaluation_status": "pending",
                    "resolved": None,
                }
            )
        summary = summarize_condition(records, expected_tasks=len(manifest["tasks"]))
        smoke_path = (
            trial_directory(output, condition, manifest["smoke_task"], smoke=True)
            / "result.json"
        )
        smoke_result = read_json(smoke_path) if smoke_path.exists() else None
        all_smokes.append(
            {
                **(
                    smoke_result
                    or {
                        "state": "pending",
                        "inference_status": "Pending",
                        "resolved": None,
                    }
                ),
                "instance_id": condition["condition_id"],
            }
        )
        report = {
            "schema_version": 1,
            "experiment_id": manifest["run_id"],
            **condition,
            "updated_at": now(),
            "release": manifest["release"],
            "release_content_sha256": manifest["release_content_sha256"],
            "limits": {
                key: manifest[key]
                for key in (
                    "step_limit",
                    "hard_timeout_seconds",
                    "max_output_tokens_per_request",
                    "per_task_cost_limit_usd",
                )
            },
            "pricing": manifest["pricing"],
            "summary": summary,
            "smoke": {
                "result": smoke_result,
                "gate_issues": smoke_issues(smoke_result)
                if smoke_result
                else ["Not run"],
                "included_in_score": False,
            },
            "by_difficulty": {
                difficulty: summarize_condition(
                    [r for r in records if r["difficulty"] == difficulty],
                    expected_tasks=count,
                )
                for difficulty, count in (("easy", 3), ("medium", 4), ("hard", 3))
            },
            "tasks": records,
        }
        atomic_write_json(directory / f"{condition['condition_id']}.json", report)
        summaries.append(
            {
                **condition,
                **summary,
                "file": f"conditions/{condition['condition_id']}.json",
            }
        )
        all_trials.extend(records)
    overall = {
        "schema_version": 1,
        "experiment_id": manifest["run_id"],
        "updated_at": now(),
        "expected_conditions": len(manifest["conditions"]),
        "expected_trials": manifest["expected_trials"],
        "summary": summarize_condition(
            [
                {**r, "instance_id": f"{r['model']}/{r['effort']}/{r['instance_id']}"}
                for r in all_trials
            ],
            expected_tasks=manifest["expected_trials"],
        ),
        "conditions": summaries,
        "smoke_summary": summarize_condition(
            all_smokes, expected_tasks=len(manifest["conditions"])
        ),
    }
    overall["combined_observed_cost_usd"] = (
        overall["summary"]["observed_cost_usd"]
        + overall["smoke_summary"]["observed_cost_usd"]
    )
    overall["combined_cost_estimate_complete"] = (
        overall["summary"]["cost_estimate_complete"]
        and overall["smoke_summary"]["cost_estimate_complete"]
    )
    atomic_write_json(output / "summary.json", overall)
    fields = [
        "model",
        "effort",
        "task_id",
        "difficulty",
        "state",
        "resolved",
        "inference_status",
        "evaluation_status",
        "failure_category",
        "inference_seconds",
        "total_seconds",
        "grading_seconds",
        "estimated_cost_usd",
        "observed_cost_usd",
        "cost_estimate_complete",
        "input_tokens",
        "cached_input_tokens",
        "cache_write_input_tokens",
        "output_tokens",
        "reasoning_tokens",
        "total_tokens",
        "usage_complete",
        "agent_query_count",
        "patch_bytes",
        "patch_sha256",
    ]
    temporary = output / ".trials.csv.tmp"
    with temporary.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for trial in all_trials:
            writer.writerow({**trial, **(trial.get("usage") or {})})
    temporary.replace(output / "trials.csv")
    return overall


def run(output, manifest, *, only_conditions=None, only_tasks=None, smoke_only=False):
    import pyarrow.parquet as pq

    conditions_by_id = {c["condition_id"]: c for c in manifest["conditions"]}
    tasks_by_id = {t["task_id"]: t for t in manifest["tasks"]}
    if (
        set(only_conditions or []) - conditions_by_id.keys()
        or set(only_tasks or []) - tasks_by_id.keys()
    ):
        raise ValueError("Unknown condition or task filter")
    rows = {
        r["instance_id"]: r
        for r in pq.read_table(output / "public/dev.parquet").to_pylist()
    }
    smoke_row = pq.read_table(output / "smoke-public/dev.parquet").to_pylist()[0]
    smoke_task = manifest["smoke_task"]
    instances = {
        i["instance_id"]: i
        for i in load_task_repo(
            manifest["task_repo"], [*rows, smoke_task["instance_id"]]
        )
    }
    locks = {iid: threading.Lock() for iid in instances}
    jobs = [
        c
        for c in manifest["conditions"]
        if not only_conditions or c["condition_id"] in only_conditions
    ]
    random.Random(manifest["schedule_seed"]).shuffle(jobs)
    session = {
        "started_at": now(),
        "scheduled_conditions": len(jobs),
        "workers": manifest["workers"],
        "smoke_only": smoke_only,
    }
    started = time.perf_counter()
    print(json.dumps(session), flush=True)
    report_lock = threading.Lock()

    def run_one(condition, task, row, *, smoke=False):
        try:
            result = execute_trial(
                output,
                manifest,
                condition,
                task,
                row,
                instances[task["instance_id"]],
                locks[task["instance_id"]],
                smoke=smoke,
            )
        except Exception as exc:
            from swebench.benchmarks.tsmc.experiment_report import summarize_trial

            directory = trial_directory(output, condition, task, smoke=smoke)
            directory.mkdir(parents=True, exist_ok=True)
            atomic_write_json(
                directory / "orchestration_error.json",
                {"error": f"{type(exc).__name__}: {exc}", "at": now()},
            )
            paths = list((directory / "inference").glob("*/*.traj.json"))
            result = summarize_trial(
                task["instance_id"],
                timing=read_partial_json(directory / "timing.json")
                if (directory / "timing.json").exists()
                else {"exit_status": "InterruptedTrial"},
                trajectory=read_partial_json(paths[0]) if paths else {},
                request_events=read_events(directory / "requests.jsonl"),
                evaluation={"status": "orchestration_error", "resolved": None},
            )
            result.update(
                task_id=task["task_id"],
                difficulty=task["difficulty"],
                model=condition["model"],
                effort=condition["effort"],
                state="completed",
                phase="smoke" if smoke else "scored",
                error=f"{type(exc).__name__}: {exc}",
            )
            atomic_write_json(directory / "result.json", result)
        with report_lock:
            refresh_reports(output, manifest)
            print(
                json.dumps(
                    {
                        "condition": condition["condition_id"],
                        "task": task["task_id"],
                        "phase": "smoke" if smoke else "scored",
                        "resolved": result["resolved"],
                        "status": result["inference_status"],
                    }
                ),
                flush=True,
            )
        return result

    def run_condition(condition):
        smoke_result = run_one(condition, smoke_task, smoke_row, smoke=True)
        issues = smoke_issues(smoke_result)
        if issues:
            print(
                json.dumps(
                    {"condition": condition["condition_id"], "blocked_by_smoke": issues}
                ),
                flush=True,
            )
            return
        if smoke_only:
            return
        tasks = [
            t for t in manifest["tasks"] if not only_tasks or t["task_id"] in only_tasks
        ]
        random.Random(manifest["schedule_seed"]).shuffle(tasks)
        for task in tasks:
            run_one(condition, task, rows[task["instance_id"]])

    with ThreadPoolExecutor(max_workers=manifest["workers"]) as pool:
        futures = [pool.submit(run_condition, condition) for condition in jobs]
        for future in as_completed(futures):
            future.result()
    session.update(ended_at=now(), wall_seconds=time.perf_counter() - started)
    sessions_path = output / "sessions.json"
    sessions = read_json(sessions_path) if sessions_path.exists() else []
    atomic_write_json(sessions_path, [*sessions, session])
    return refresh_reports(output, manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, default=Path(".generated/tsmc/public"))
    parser.add_argument(
        "--task-repo", type=Path, default=Path(".generated/tsmc/task-repo")
    )
    parser.add_argument("--run-id", default="tsmc-openai-matrix-20260912")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--steps", type=int, default=50)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--smoke-only", action="store_true")
    parser.add_argument("--condition", action="append")
    parser.add_argument("--task", action="append")
    args = parser.parse_args()
    args.output = args.output.resolve()
    manifest = (
        verify_resume(args.output)
        if args.resume
        else prepare(
            args.output,
            args.dataset,
            args.task_repo,
            run_id=args.run_id,
            workers=args.workers,
            steps=args.steps,
            timeout=args.timeout,
        )
    )
    with experiment_lock(args.output):
        if not args.prepare_only:
            run(
                args.output,
                manifest,
                only_conditions=args.condition,
                only_tasks=args.task,
                smoke_only=args.smoke_only,
            )


if __name__ == "__main__":
    main()
