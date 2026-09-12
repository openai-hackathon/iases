"""Scenario input binding, run ownership and native grade receipt validation."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import time
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from swebench.benchmarks.tsmc.prepare import prepare
from swebench.benchmarks.tsmc.scenario import docker, runner
from swebench.cli.scenario import scenario_app
from swebench.task.repo import load_task_repo

SOURCE = Path(__file__).resolve().parents[1] / "benchmarks/tsmc"


@pytest.fixture(scope="module")
def task_repo(tmp_path_factory):
    generated = tmp_path_factory.mktemp("scenario-runner") / "generated"
    prepare(
        SOURCE,
        generated,
        [f"{track}{index:02}" for track in "FAR" for index in range(1, 5)],
    )
    return generated / "task-repo"


@pytest.mark.parametrize(
    "change", ["source", "mapping", "edition", "duplicate", "config"]
)
def test_mismatched_scenario_inputs_rejected(task_repo, tmp_path, monkeypatch, change):
    source = tmp_path / "source"
    shutil.copytree(SOURCE, source)
    rows = deepcopy(load_task_repo(task_repo))
    row = next(row for row in rows if row["task_id"] == "F01")
    if change == "source":
        path = source / "tasks/F01/task.json"
        path.write_text(path.read_text() + "\n")
    elif change == "mapping":
        path = source / "scenarios/author/DC01/source_map.json"
        mapping = json.loads(path.read_text())
        mapping["release"]["task_id"] = "R02"
        path.write_text(json.dumps(mapping))
    elif change == "edition":
        row["source_manifest_sha256"] = "0" * 64
    elif change == "duplicate":
        rows.append(dict(row, instance_id="tsmc__f01-another-version"))
    else:
        copied = tmp_path / "task-repo"
        shutil.copytree(task_repo, copied)
        task_repo = copied
        path = copied / "tasks" / row["instance_id"] / "tsmc.json"
        config = json.loads(path.read_text())
        config["public_hashes"]["fabops/eligibility.py"] = "0" * 64
        path.write_text(json.dumps(config))
    monkeypatch.setattr(runner, "load_task_repo", lambda path: rows)
    with pytest.raises(ValueError, match="map|mismatch|exactly one"):
        runner.scenario_inputs(source, task_repo, "DC01")


@pytest.mark.parametrize("late", [False, True])
def test_no_available_predictions_needs_no_docker(
    task_repo, tmp_path, monkeypatch, late
):
    def unexpected_backend(*args, **kwargs):
        pytest.fail("No patch within the horizon should require Docker")

    monkeypatch.setattr(runner, "DockerBackend", unexpected_backend)
    monkeypatch.setattr(runner, "RUN_EVALUATION_LOG_DIR", tmp_path / "native")
    predictions = tmp_path / "predictions.json"
    predictions.write_text(
        json.dumps(
            [dict(instance_id="tsmc__f01-v0.2", model_patch="patch")] if late else []
        )
    )
    availability = tmp_path / "availability.json"
    availability.write_text(json.dumps({"release": 241}))
    directory, report = runner.run(
        "DC02",
        "empty",
        source=SOURCE,
        task_repo=task_repo,
        predictions=predictions,
        availability=availability,
        output=tmp_path / "trials",
    )
    assert report["restored_rate"] == report["verified_rate"] == 0
    assert report["service_count"] == 6
    assert all(service["not_submitted"] for service in report["services"].values())
    assert report["services"]["telemetry"]["unavailable_seconds"] == 120
    assert json.loads((directory / "manifest.json").read_text())["images"] == {}


def test_partial_predictions_only_require_submitted_images(
    task_repo, tmp_path, monkeypatch
):
    class Backend:
        def __init__(self, repo, instances, run_id, output, configs):
            assert set(instances) == set(configs) == {"release"}
            self.images = {"release": "sha256:test-image"}

        def grade(self, service, patch, submitted):
            return dict(
                service=service,
                patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),
                resolved=True,
            )

        def invoke(self, *args):
            pytest.fail("Unrestored dependencies must prevent release probes")

    monkeypatch.setattr(runner, "DockerBackend", Backend)
    monkeypatch.setattr(runner, "RUN_EVALUATION_LOG_DIR", tmp_path / "native")
    predictions = tmp_path / "predictions.json"
    predictions.write_text(
        json.dumps([dict(instance_id="tsmc__f01-v0.2", model_patch="patch")])
    )
    directory, report = runner.run(
        "DC01",
        "partial",
        source=SOURCE,
        task_repo=task_repo,
        predictions=predictions,
        output=tmp_path / "trials",
    )
    assert report["verified_rate"] == 1 / 8 and report["restored_rate"] == 0
    manifest = json.loads((directory / "manifest.json").read_text())
    assert len(manifest["tasks"]) == 8 and len(manifest["images"]) == 1


def test_same_native_run_cannot_be_claimed_from_different_outputs(tmp_path):
    native = tmp_path / "native/shared"

    def claim(index):
        output = tmp_path / f"output-{index}/shared"
        try:
            runner.claim_trial(output, native)
            return output
        except ValueError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        winners = [path for path in pool.map(claim, range(2)) if path]
    assert len(winners) == 1 and winners[0].is_dir() and native.is_dir()


@pytest.mark.parametrize("failure", ["patch", "baseline", "instance", "connection"])
def test_native_grade_must_match_submission(task_repo, tmp_path, monkeypatch, failure):
    row = next(row for row in load_task_repo(task_repo) if row["task_id"] == "F01")
    backend = object.__new__(docker.DockerBackend)
    backend.instances, backend.images = {"release": row}, {"release": "sha256:image"}
    backend.configs = {"release": {"test_timeout": 5}}
    backend.run_id, backend.task_repo = "receipt-test", task_repo
    patch = row["patch"]
    detail = dict(
        patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),
        base_commit=row["base_commit"],
        instance_id=row["instance_id"],
        resolved=True,
    )
    field = {
        "patch": "patch_sha256",
        "baseline": "base_commit",
        "instance": "instance_id",
    }
    if failure in field:
        detail[field[failure]] = "stale"

    def client():
        if failure == "connection":
            raise OSError("Docker unavailable")
        return SimpleNamespace(close=lambda: None)

    monkeypatch.setattr(docker, "_docker_client", client)
    monkeypatch.setattr(docker, "RUN_EVALUATION_LOG_DIR", tmp_path / "native")
    monkeypatch.setattr(
        docker,
        "run_instance",
        lambda *args, **kwargs: (
            row["instance_id"],
            {row["instance_id"]: {"resolved": True}},
        ),
    )
    monkeypatch.setattr(docker, "read_result", lambda path: detail)
    receipt = backend.grade("release", patch, time.monotonic())
    assert not receipt["resolved"] and receipt["error"]
    assert "log_dir" in receipt and receipt["wall_seconds"] >= 0


def test_cli_reports_missing_prediction_file(task_repo, tmp_path):
    result = CliRunner().invoke(
        scenario_app,
        [
            "run",
            "DC01",
            "--trial-id",
            "missing-predictions",
            "--task-repo",
            str(task_repo),
            "--source",
            str(SOURCE),
            "-p",
            str(tmp_path / "missing.json"),
        ],
    )
    assert result.exit_code == 2 and "missing.json" in result.output


def test_cli_rejects_malformed_receipts_without_overwriting_report(tmp_path):
    (tmp_path / "events.jsonl").write_text("null\n")
    saved = tmp_path / "report.json"
    saved.write_text("existing report")
    result = CliRunner().invoke(scenario_app, ["report", str(tmp_path)])
    assert result.exit_code == 2 and "Malformed receipt" in result.output
    assert saved.read_text() == "existing report"
