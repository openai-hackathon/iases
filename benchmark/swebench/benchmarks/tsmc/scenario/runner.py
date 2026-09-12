"""Evaluate standard SWE-bench predictions in a synthetic incident replay."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import time

from swebench.benchmarks.tsmc.common import file_hashes
from swebench.benchmarks.tsmc.jsonio import decode_json, read_json
from swebench.benchmarks.tsmc.prepare import write_json
from swebench.harness.constants import RUN_EVALUATION_LOG_DIR
from swebench.task.publish import guard
from swebench.task.repo import load_task_repo

from .docker import DockerBackend
from .engine import replay
from .events import EventLog, seconds
from .probes import CONTRACT_VERSION, probe
from .reporting import summarize
from .state import validate


def predictions_from(path):
    path = Path(path)
    if path.suffix == ".jsonl":
        rows = [
            decode_json(line, f"prediction at {path}:{index}")
            for index, line in enumerate(path.read_text().splitlines(), 1)
            if line.strip()
        ]
    else:
        rows = read_json(path)
        if isinstance(rows, dict):
            expanded = []
            for key, value in rows.items():
                if not isinstance(value, dict) or value.get("instance_id", key) != key:
                    raise ValueError(
                        f"Prediction mapping key conflicts with its record: {key}"
                    )
                expanded.append(dict(value, instance_id=key))
            rows = expanded
    if not isinstance(rows, list):
        raise ValueError(
            "Predictions must be an array, JSONL records, or an instance mapping"
        )
    predictions = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Each prediction must be an object")
        iid = row.get("instance_id")
        if not isinstance(iid, str) or not iid.strip():
            raise ValueError("Prediction instance_id must be a nonempty string")
        if iid in predictions or not isinstance(row.get("model_patch"), str):
            raise ValueError(f"Duplicate prediction instance or invalid patch: {iid}")
        if not isinstance(row.get("model_name_or_path", "unspecified"), str):
            raise ValueError(f"Prediction model_name_or_path must be a string: {iid}")
        predictions[iid] = row
    return predictions


def scenario_inputs(source, task_repo, scenario_id):
    """Bind the scenario's source map to the exact generated task edition."""
    scenario_dir = source / "scenarios" / "author" / scenario_id
    spec = read_json(scenario_dir / "scenario.json")
    validate(spec)
    if spec["scenario_id"] != scenario_id:
        raise ValueError("Scenario ID does not match the selected directory")
    mapping = read_json(scenario_dir / "source_map.json")
    if not isinstance(mapping, dict) or set(mapping) != set(spec["services"]):
        raise ValueError("Scenario source map must cover exactly its services")
    guard(task_repo)
    by_task = {}
    for row in load_task_repo(task_repo):
        by_task.setdefault(row.get("task_id"), []).append(row)
    instances, configs = {}, {}
    for sid, cfg in spec["services"].items():
        task = cfg["task_id"]
        entry = mapping[sid]
        if not isinstance(entry, dict) or entry.get("task_id") != task:
            raise ValueError(f"Source map task mismatch for {sid}")
        task_path = source / "tasks" / task / "task.json"
        source_sha = hashlib.sha256(task_path.read_bytes()).hexdigest()
        if entry.get("source_task_manifest_sha256") != source_sha:
            raise ValueError(f"Stale source map for {sid}/{task}")
        candidates = by_task.get(task, [])
        if len(candidates) != 1:
            raise ValueError(
                f"Task repo must contain exactly one instance for {sid}/{task}"
            )
        row = candidates[0]
        if row.get("source_manifest_sha256") != source_sha:
            raise ValueError(
                f"Generated task source mismatch for {sid}/{task}; regenerate the task repo"
            )
        config = read_json(task_repo / "tasks" / row["instance_id"] / "tsmc.json")
        metadata = read_json(task_path)
        if (
            not isinstance(config, dict)
            or config.get("instance_id") != row["instance_id"]
            or config.get("base_commit") != row["base_commit"]
            or config.get("task_id") != task
            or config.get("public_hashes") != metadata["agent_file_sha256"]
        ):
            raise ValueError(
                f"Generated evaluator configuration mismatch for {sid}/{task}"
            )
        instances[sid], configs[sid] = row, config
    return spec, instances, configs


def claim_trial(directory, native_directory):
    """Claim the shared native run ID even when callers choose different outputs."""
    directory.parent.mkdir(parents=True, exist_ok=True)
    native_directory.parent.mkdir(parents=True, exist_ok=True)
    try:
        native_directory.mkdir()
    except FileExistsError as exc:
        raise ValueError(
            "Use a fresh trial_id; native evaluation artifacts already exist"
        ) from exc
    try:
        directory.mkdir()
    except OSError as exc:
        # This directory was just created by this claim and contains no logs.
        native_directory.rmdir()
        if isinstance(exc, FileExistsError):
            raise ValueError(
                "Use a fresh trial_id; trial artifacts already exist"
            ) from exc
        raise


def run(
    scenario_id,
    trial_id,
    *,
    source=Path("benchmarks/tsmc"),
    task_repo=Path(".generated/tsmc/task-repo"),
    predictions=None,
    gold=False,
    availability=None,
    horizon=240,
    workers=2,
    output=Path("logs/scenarios"),
):
    if not re.fullmatch(r"DC0[1-4]", scenario_id):
        raise ValueError("Expected DC01, DC02, DC03 or DC04")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", trial_id):
        raise ValueError("Use a trial ID of up to 80 letters, digits, _, . or -")
    if bool(gold) == (predictions is not None):
        raise ValueError("Supply exactly one of gold or predictions")
    if type(workers) is not int or workers < 1:
        raise ValueError("workers must be positive")
    horizon = seconds(horizon)
    source, task_repo = Path(source).resolve(), Path(task_repo).resolve()
    spec, instances, configs = scenario_inputs(source, task_repo, scenario_id)
    if predictions is not None:
        supplied = predictions_from(predictions)
    else:
        supplied = {
            row["instance_id"]: dict(
                model_patch=row["patch"], model_name_or_path="gold"
            )
            for row in instances.values()
        }
    if supplied and not set(supplied).intersection(
        row["instance_id"] for row in instances.values()
    ):
        raise ValueError("Predictions do not match any instance in this scenario")
    available = read_json(availability) if availability else {}
    if not isinstance(available, dict):
        raise ValueError("Availability trace must be a service-to-seconds object")
    if set(available) - set(instances):
        raise ValueError("Availability trace contains an unknown service")
    available = {sid: seconds(available.get(sid, 0)) for sid in instances}
    directory, native_run = Path(output).resolve() / trial_id, f"scenario-{trial_id}"
    if directory.exists() or (RUN_EVALUATION_LOG_DIR / native_run).exists():
        raise ValueError("Use a fresh trial_id; prior artifacts must not be reused")
    patches = {
        sid: supplied[row["instance_id"]]["model_patch"]
        for sid, row in instances.items()
        if row["instance_id"] in supplied and available[sid] <= horizon
    }
    selected = {sid: instances[sid] for sid in patches}
    backend = (
        DockerBackend(
            task_repo,
            selected,
            native_run,
            directory,
            configs={sid: configs[sid] for sid in selected},
        )
        if selected
        else None
    )
    claim_trial(directory, RUN_EVALUATION_LOG_DIR / native_run)
    write_json(
        directory / "manifest.json",
        dict(
            schema="tsmc-trial/1",
            trial_id=trial_id,
            scenario_id=scenario_id,
            mode="precomputed-patch-replay",
            candidate_source="bundled-gold" if gold else "predictions",
            synthetic=True,
            horizon_seconds=horizon,
            workers=workers,
            probe_workers=1,
            contract_version=CONTRACT_VERSION,
            availability_seconds=available,
            source_hashes=file_hashes(source / "scenarios" / "author" / scenario_id),
            implementation_hashes=file_hashes(Path(__file__).parent),
            native_run_id=native_run,
            images=backend.images if backend else {},
            tasks={
                sid: dict(
                    instance_id=row["instance_id"],
                    base_commit=row["base_commit"],
                    task_config_sha256=hashlib.sha256(
                        json.dumps(configs[sid], sort_keys=True).encode()
                    ).hexdigest(),
                )
                for sid, row in instances.items()
            },
            models={
                sid: supplied[row["instance_id"]].get(
                    "model_name_or_path", "unspecified"
                )
                for sid, row in instances.items()
                if row["instance_id"] in supplied
            },
        ),
    )
    for sid, patch in patches.items():
        patch_dir = directory / "patches"
        patch_dir.mkdir(exist_ok=True)
        (patch_dir / f"{sid}.patch").write_text(patch)
    submitted = time.monotonic()

    def grade(sid):
        receipt = backend.grade(sid, patches[sid], submitted)
        receipt["at_seconds"] = available[sid]
        return receipt

    # All local repairs are independent of the restoration graph. No waiting
    # dependency occupies a grader slot. The order is stable FIFO by manifest.
    with ThreadPoolExecutor(max_workers=workers) as pool:
        grades = list(pool.map(grade, patches))
    write_json(directory / "grades.json", grades)

    def compose(sid, evidence, upstream):
        patch = patches[sid]
        if hashlib.sha256(patch.encode()).hexdigest() != evidence["patch"]:
            raise ValueError("Candidate changed after grading")
        start = time.monotonic()
        result = probe(
            sid,
            instances[sid]["task_id"],
            upstream,
            lambda service, payload: backend.invoke(service, patch, payload),
        )
        result["wall_seconds"] = time.monotonic() - start
        return result

    log = EventLog(trial_id, scenario_id, directory / "events.jsonl")
    events = replay(spec, grades, compose, trial_id=trial_id, horizon=horizon, log=log)
    report = summarize(events)
    write_json(directory / "report.json", report)
    return directory, report
