"""Measure repeated public-task inference with two independent, bounded workers.

Each instance runs in an owned subprocess, so the timeout is a hard wall-clock
limit including process and container startup. This adds startup overhead versus
one long-lived mini-SWE-agent batch; reports explicitly identify that scope.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import secrets
import shutil
import signal
import subprocess
import sys
import time

from swebench.task.repo import dump_yaml, load_yaml
from swebench.inference.workspace_agent import atomic_write_json


def write_json(path, value):
    atomic_write_json(path, value)


def check_disk_space(path, minimum_bytes):
    existing = path.resolve()
    while not existing.exists():
        existing = existing.parent
    free = shutil.disk_usage(existing).free
    if free < minimum_bytes:
        raise ValueError(
            f"Insufficient disk space for inference artifacts: {free} bytes free; {minimum_bytes} required"
        )


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def prepare_config(paths, *, steps, timeout, endpoint=None, model_name=None):
    """Merge agent/provider files without imposing provider-specific parameters."""
    from minisweagent.utils.serialize import recursive_merge

    configs = []
    for path in paths:
        config = load_yaml(path)
        if not isinstance(config, dict):
            raise ValueError(f"Configuration must contain a mapping: {path}")
        configs.append(config)
    config = recursive_merge(*configs)
    for section in ("agent", "environment", "model"):
        if not isinstance(config.setdefault(section, {}), dict):
            raise ValueError(f"Configuration section must contain a mapping: {section}")
    config["agent"].update(step_limit=steps, wall_time_limit_seconds=timeout)
    model = config["model"]
    kwargs = model.setdefault("model_kwargs", {})
    if not isinstance(kwargs, dict):
        raise ValueError("model.model_kwargs must contain a mapping")
    if model_name:
        model["model_name"] = model_name
    if endpoint is not None:
        endpoint = endpoint.rstrip("/")
        kwargs["api_base"] = endpoint if endpoint.endswith("/v1") else endpoint + "/v1"
    for name in ("fallbacks", "context_window_fallbacks", "model_list"):
        if name in model or name in kwargs:
            raise ValueError(
                "Alternate model routes are not permitted in this timing experiment"
            )
    return config


def run_instance(
    row,
    directory,
    config,
    dataset,
    split,
    limit,
    *,
    retry_attempts=2,
    request_log_path=None,
):
    """Run one fresh trial; preserve failures without repeating a completed run.

    Request-level usage belongs in the model adapter's journal. The returned
    model_stats are the unmodified agent statistics and can lag an in-flight
    request when the outer hard deadline terminates the process.
    """
    import docker
    import minisweagent

    if retry_attempts < 1:
        raise ValueError("Model retry attempts must be positive")
    directory.mkdir(parents=True, exist_ok=False)
    label = hashlib.sha256(str(directory.resolve()).encode()).hexdigest()
    config = json.loads(json.dumps(config))
    if request_log_path is not None:
        config.setdefault("model", {})["request_log_path"] = str(
            Path(request_log_path).resolve()
        )
    config["environment"].setdefault("run_args", []).extend(
        ["--label", f"tsmc-bench.timing={label}"]
    )
    config_path = directory / "config.yaml"
    config.setdefault("agent", {})["output_path"] = str(
        directory / "inference" / row["instance_id"] / f"{row['instance_id']}.traj.json"
    )
    config_path.write_text(dump_yaml(config))
    default = Path(minisweagent.__file__).parent / "config/benchmarks/swebench.yaml"
    import re

    module = (
        "swebench.inference.workspace_agent"
        if config.get("run", {}).get("collect_workspace")
        else "minisweagent.run.benchmarks.swebench"
    )
    command = [
        sys.executable,
        "-m",
        module,
        "--subset",
        str(dataset),
        "--split",
        split,
        "--filter",
        "^" + re.escape(row["instance_id"]) + "$",
        "-w",
        "1",
        "-o",
        str(directory / "inference"),
        "-c",
        str(default),
        "-c",
        str(config_path),
    ]
    started_at, started = utc_now(), time.perf_counter()
    timed_out, return_code, process_error = False, None, None
    env = dict(
        os.environ,
        MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT=str(retry_attempts),
        MSWEA_SILENT_STARTUP="1",
        LITELLM_LOG="ERROR",
        HF_DATASETS_CACHE=str((dataset.parent / "cache").resolve()),
    )
    cleanup_errors = []
    with (directory / "console.log").open("w") as output:
        try:
            process = subprocess.Popen(
                command,
                stdout=output,
                stderr=subprocess.STDOUT,
                env=env,
                start_new_session=True,
            )
            return_code = process.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                return_code = process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                return_code = process.wait()
        except OSError as exc:
            process_error = f"{type(exc).__name__}: {exc}"
        inference_seconds = time.perf_counter() - started
    inference_ended_at = utc_now()
    cleanup_started = time.perf_counter()
    paths = list((directory / "inference").glob("*/*.traj.json"))
    trajectory_path = paths[0] if paths else None
    trajectory_error = None
    try:
        trajectory = json.loads(paths[0].read_text()) if paths else {"info": {}}
        if not isinstance(trajectory, dict) or not isinstance(
            trajectory.get("info"), dict
        ):
            raise ValueError("Trajectory must contain an info mapping")
    except (ValueError, OSError) as exc:
        trajectory_error = str(exc)
        trajectory = {"info": {}}
    info = trajectory["info"]
    # Recover edits after a hard stop, then remove only this trial's containers.
    try:
        client = docker.from_env(timeout=30)
        try:
            containers = client.containers.list(
                all=True, filters={"label": f"tsmc-bench.timing={label}"}
            )
            try:
                if timed_out and config.get("run", {}).get("collect_workspace"):
                    from swebench.inference.workspace_agent import (
                        collect_container_patch,
                    )

                    if len(containers) != 1:
                        raise ValueError(
                            "Expected exactly one owned workspace for patch recovery"
                        )
                    patch = collect_container_patch(
                        containers[0],
                        row["base_commit"],
                        row["instance_id"],
                        config["environment"],
                    )
                    info.update(
                        model_exit_status=info.get("model_exit_status")
                        or info.get("exit_status")
                        or "HardTimeout",
                        model_submission=info.get(
                            "model_submission", info.get("submission", "")
                        ),
                        exit_status="HardTimeout",
                        submission=patch,
                        submission_source="workspace_diff_after_timeout",
                        patch_baseline=row["base_commit"],
                    )
                    path = (
                        paths[0]
                        if paths
                        else directory
                        / "inference"
                        / row["instance_id"]
                        / f"{row['instance_id']}.traj.json"
                    )
                    path.parent.mkdir(parents=True, exist_ok=True)
                    write_json(path, trajectory)
                    trajectory_path = path
                    write_json(
                        directory / "inference" / "preds.json",
                        {
                            row["instance_id"]: {
                                "instance_id": row["instance_id"],
                                "model_name_or_path": config.get("model", {}).get(
                                    "model_name", "unknown"
                                ),
                                "model_patch": patch,
                            }
                        },
                    )
            except Exception as exc:
                info["patch_collection_error"] = str(exc)
                write_json(
                    directory / "patch-collection-error.json", {"error": str(exc)}
                )
            finally:
                for container in containers:
                    try:
                        container.remove(force=True)
                    except Exception as exc:
                        cleanup_errors.append(str(exc))
        finally:
            client.close()
    except Exception as exc:
        cleanup_errors.append(str(exc))
    if timed_out:
        status = "HardTimeout"
    elif process_error:
        status = "ProcessError"
    elif trajectory_error:
        status = "InvalidTrajectory"
    elif paths:
        status = info.get("exit_status") or "IncompleteTrajectory"
    else:
        status = "MissingTrajectory"
    stats = info.get("model_stats")
    model_stats = stats if isinstance(stats, dict) else {}
    prediction_path = directory / "inference" / "preds.json"
    result = dict(
        instance_id=row["instance_id"],
        started_at=started_at,
        inference_ended_at=inference_ended_at,
        ended_at=utc_now(),
        inference_seconds=inference_seconds,
        cleanup_seconds=time.perf_counter() - cleanup_started,
        total_seconds=time.perf_counter() - started,
        exit_status=status,
        subprocess_return_code=return_code,
        hard_timeout=timed_out,
        process_error=process_error,
        model_retry_attempts=retry_attempts,
        cleanup_errors=cleanup_errors,
        api_calls=model_stats.get("api_calls"),
        model_stats=model_stats,
        request_log_path=config.get("model", {}).get("request_log_path"),
        trajectory_path=str(trajectory_path) if trajectory_path else None,
        prediction_path=str(prediction_path) if prediction_path.exists() else None,
        nonempty_submission=bool((info.get("submission") or "").strip()),
        patch_collection_error=info.get("patch_collection_error"),
        trajectory_error=trajectory_error,
    )
    write_json(directory / "timing.json", result)
    print(
        f"{directory.parent.name} {row['instance_id']}: {status}, {result['total_seconds']:.2f}s",
        flush=True,
    )
    return result


def main():
    from datasets import load_dataset

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--split", choices=["demo_dev", "dev"], default="demo_dev")
    parser.add_argument(
        "--config",
        type=Path,
        action="append",
        required=True,
        help="Agent/provider YAML; repeat to merge in order, with later values winning",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--endpoint", help="Optional API base override, with or without a /v1 suffix"
    )
    parser.add_argument("--model", help="Override the configured provider/model name")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--steps", type=int, default=50)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument(
        "--seed", type=int, help="Task sampling seed; never sent to the API"
    )
    parser.add_argument(
        "--model-seed",
        type=int,
        help="Optional API seed for round one, incremented each round; use only with models that support seed",
    )
    parser.add_argument(
        "--min-free-mb",
        type=int,
        default=1024,
        help="Required free host disk space before inference starts",
    )
    args = parser.parse_args()
    if min(args.count, args.workers, args.rounds, args.steps, args.timeout) <= 0:
        parser.error("Counts and budgets must be positive")
    if args.min_free_mb < 0:
        parser.error("Minimum free disk space cannot be negative")
    try:
        config = prepare_config(
            args.config,
            steps=args.steps,
            timeout=args.timeout,
            endpoint=args.endpoint,
            model_name=args.model,
        )
        check_disk_space(args.output, args.min_free_mb * 1024**2)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    import pyarrow.parquet as parquet

    rows = sorted(
        parquet.read_table(args.dataset / f"{args.split}.parquet").to_pylist(),
        key=lambda r: r["instance_id"],
    )
    if args.count > len(rows):
        parser.error("Sample exceeds the public split")
    seed = args.seed if args.seed is not None else secrets.randbits(32)
    selected = random.Random(seed).sample(rows, args.count)
    args.output.mkdir(parents=True, exist_ok=False)
    frozen = args.output / "public"
    frozen.mkdir()
    from datasets import Dataset

    Dataset.from_list(selected).to_parquet(str(frozen / f"{args.split}.parquet"))
    fingerprint = hashlib.sha256(
        (frozen / f"{args.split}.parquet").read_bytes()
    ).hexdigest()[:16]
    metadata = {
        "configs": [
            {
                "config_name": f"sample-{fingerprint}",
                "data_files": [{"split": args.split, "path": f"{args.split}.parquet"}],
            }
        ]
    }
    (frozen / "README.md").write_text(
        "---\n" + dump_yaml(metadata) + "---\nPublic timing sample.\n"
    )
    if (
        len(
            load_dataset(
                str(frozen), split=args.split, cache_dir=str(args.output / "cache")
            )
        )
        != args.count
    ):
        parser.error("Frozen public sample did not round-trip")
    manifest = dict(
        seed=seed,
        dataset=str(args.dataset),
        split=args.split,
        instances=[r["instance_id"] for r in selected],
        endpoint=config["model"]["model_kwargs"].get("api_base"),
        model_name=config["model"].get("model_name"),
        model_class=config["model"].get("model_class"),
        model_seed=args.model_seed,
        workers=args.workers,
        rounds=args.rounds,
        step_limit=args.steps,
        hard_timeout_seconds=args.timeout,
        scope="Per-instance subprocess startup, inference and owned-container cleanup; no image builds or grading",
        config_sha256=hashlib.sha256(dump_yaml(config).encode()).hexdigest(),
    )
    write_json(args.output / "manifest.json", manifest)
    print(json.dumps(manifest, indent=2), flush=True)
    rounds = []
    for index in range(1, args.rounds + 1):
        current = args.output / f"round-{index}"
        current.mkdir()
        if args.model_seed is not None:
            config["model"]["model_kwargs"]["seed"] = args.model_seed + index - 1
        started_at, start = utc_now(), time.perf_counter()
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            results = list(
                pool.map(
                    lambda row: run_instance(
                        row,
                        current / row["instance_id"],
                        config,
                        frozen,
                        args.split,
                        args.timeout,
                    ),
                    selected,
                )
            )
        summary = dict(
            round=index,
            started_at=started_at,
            ended_at=utc_now(),
            elapsed_seconds=time.perf_counter() - start,
            tasks=results,
        )
        write_json(current / "summary.json", summary)
        rounds.append(summary)
        write_json(args.output / "summary.json", dict(manifest=manifest, rounds=rounds))
        print(f"ROUND {index}: {summary['elapsed_seconds']:.2f}s", flush=True)


if __name__ == "__main__":
    main()
