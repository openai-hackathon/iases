"""Experiment resumes preserve paid trials and independently verify grading evidence."""

from collections import Counter
import copy
import hashlib
import json
import threading
from types import SimpleNamespace

import pytest

from swebench.benchmarks.tsmc import GATE_TEST, experiment
from swebench.inference.workspace_agent import atomic_write_json


def public_selection():
    rows, metadata = [], []
    for index, task_id in enumerate(experiment.TASK_IDS):
        iid = f"tsmc__{task_id.lower()}-v1.0"
        difficulty = "easy" if index < 3 else "medium" if index < 7 else "hard"
        rows.append(
            {
                "task_id": task_id,
                "instance_id": iid,
                "repo": "synthetic/fabops",
                "version": "1.0",
                "base_commit": "a" * 40,
                "image_name": "sha256:" + "b" * 64,
                "problem_statement": "Repair the public production issue.",
            }
        )
        metadata.append(
            {
                "task_id": task_id,
                "instance_id": iid,
                "split": "dev",
                "design_difficulty": difficulty,
                "family": f"family_{task_id}",
                "required_tests": 17,
            }
        )
    return rows, {"tasks": metadata}


def test_public_sample_is_same_ten_dev_tasks_with_fixed_difficulty_mix():
    rows, release = public_selection()
    selected, metadata = experiment.select_tasks(list(reversed(rows)), release)
    assert [row["task_id"] for row in selected] == list(experiment.TASK_IDS)
    assert all(set(row) == experiment.PUBLIC_COLUMNS for row in selected)
    assert all(row["split"] == "dev" for row in metadata)
    assert Counter(row["difficulty"] for row in metadata) == {
        "easy": 3,
        "medium": 4,
        "hard": 3,
    }
    assert len(experiment.conditions()) == 23
    assert len({c["condition_id"] for c in experiment.conditions()}) == 23


@pytest.mark.parametrize(
    "corruption", ["hidden_column", "heldout", "wrong_difficulty", "duplicate"]
)
def test_public_selection_rejects_protocol_drift(corruption):
    rows, release = public_selection()
    if corruption == "hidden_column":
        rows[0]["patch"] = "hidden reference fix"
    elif corruption == "heldout":
        release["tasks"][0]["split"] = "test"
    elif corruption == "wrong_difficulty":
        release["tasks"][0]["design_difficulty"] = "hard"
    else:
        rows.append(copy.deepcopy(rows[0]))
    with pytest.raises(ValueError):
        experiment.select_tasks(rows, release)


def trial_fixture(tmp_path):
    condition = experiment.conditions()[0]
    task = {
        "task_id": "F25",
        "instance_id": "tsmc__f25-v1.0",
        "difficulty": "hard",
        "image_id": "sha256:" + "a" * 64,
    }
    manifest = {
        "configs": {condition["condition_id"]: {}},
        "hard_timeout_seconds": 600,
        "task_repo": str(tmp_path / "native"),
        "run_id": "unique-experiment",
    }
    return (
        manifest,
        condition,
        task,
        experiment.trial_directory(tmp_path, condition, task),
    )


def test_completed_trial_resume_never_calls_solver_or_grader(tmp_path, monkeypatch):
    manifest, condition, task, directory = trial_fixture(tmp_path)
    expected = {
        "instance_id": task["instance_id"],
        "state": "completed",
        "resolved": False,
    }
    atomic_write_json(directory / "result.json", expected)
    monkeypatch.setattr(
        experiment.timing,
        "run_instance",
        lambda *args, **kwargs: pytest.fail("Paid solver rerun"),
    )
    monkeypatch.setattr(
        experiment,
        "grade_trial",
        lambda *args, **kwargs: pytest.fail("Unexpected regrading"),
    )
    actual = experiment.execute_trial(
        tmp_path, manifest, condition, task, {}, {}, threading.Lock()
    )
    assert actual == expected


def test_interrupted_trial_without_timing_is_never_silently_rerun(
    tmp_path, monkeypatch
):
    manifest, condition, task, directory = trial_fixture(tmp_path)
    directory.mkdir(parents=True)
    journal = directory / "requests.jsonl"
    journal.write_text(
        json.dumps({"event": "request_started", "request_id": "paid-inflight"}) + "\n"
    )
    monkeypatch.setattr(
        experiment.timing,
        "run_instance",
        lambda *args, **kwargs: pytest.fail("Paid solver rerun"),
    )
    with pytest.raises(ValueError, match="will not be silently rerun"):
        experiment.execute_trial(
            tmp_path, manifest, condition, task, {}, {}, threading.Lock()
        )
    assert journal.exists()
    assert not (directory / "result.json").exists()


def test_resume_after_solver_completion_only_grades_saved_patch(tmp_path, monkeypatch):
    manifest, condition, task, directory = trial_fixture(tmp_path)
    iid, patch = task["instance_id"], "diff --git a/a.py b/a.py\n"
    atomic_write_json(
        directory / "timing.json",
        {
            "exit_status": "Submitted",
            "inference_seconds": 9.0,
            "total_seconds": 10.0,
            "nonempty_submission": True,
        },
    )
    atomic_write_json(
        directory / "inference" / iid / f"{iid}.traj.json",
        {"info": {"submission": patch, "model_stats": {"api_calls": 1}}},
    )
    atomic_write_json(
        directory / "inference/preds.json",
        {iid: {"instance_id": iid, "model_patch": patch}},
    )
    monkeypatch.setattr(
        experiment.timing,
        "run_instance",
        lambda *args, **kwargs: pytest.fail("Paid solver rerun"),
    )
    calls = []

    def grade(instance, prediction, **kwargs):
        calls.append((prediction, kwargs))
        return {"status": "graded", "resolved": True, "grading_seconds": 2.0}

    monkeypatch.setattr(experiment, "grade_trial", grade)
    result = experiment.execute_trial(
        tmp_path, manifest, condition, task, {}, {}, threading.Lock()
    )
    assert len(calls) == 1 and calls[0][0]["model_patch"] == patch
    assert calls[0][1]["run_id"].endswith(condition["condition_id"])
    assert calls[0][1]["image_id"] == task["image_id"]
    assert result["resolved"] is True
    assert result["patch_sha256"] == hashlib.sha256(patch.encode()).hexdigest()
    assert result["estimated_cost_usd"] is None
    assert result["cost_estimate_complete"] is False
    repeated = experiment.execute_trial(
        tmp_path, manifest, condition, task, {}, {}, threading.Lock()
    )
    assert repeated == result and len(calls) == 1


def test_prediction_and_workspace_disagreement_prevents_grading(tmp_path, monkeypatch):
    manifest, condition, task, directory = trial_fixture(tmp_path)
    iid = task["instance_id"]
    atomic_write_json(directory / "timing.json", {"exit_status": "Submitted"})
    atomic_write_json(
        directory / "inference" / iid / f"{iid}.traj.json",
        {"info": {"submission": "actual workspace"}},
    )
    atomic_write_json(
        directory / "inference/preds.json", {iid: {"model_patch": "different patch"}}
    )
    monkeypatch.setattr(
        experiment,
        "grade_trial",
        lambda *args, **kwargs: pytest.fail("Mismatched patch graded"),
    )
    result = experiment.execute_trial(
        tmp_path, manifest, condition, task, {}, {}, threading.Lock()
    )
    assert result["evaluation"]["status"] == "submission_mismatch"
    assert result["resolved"] is None


def mock_native_grade(tmp_path, monkeypatch, *, canonical, native=None):
    import docker
    from swebench.benchmarks.tsmc import validate
    from swebench.harness import constants, run_evaluation, utils

    calls = []
    monkeypatch.setattr(constants, "RUN_EVALUATION_LOG_DIR", tmp_path)
    monkeypatch.setattr(
        docker, "from_env", lambda **kwargs: SimpleNamespace(close=lambda: None)
    )
    monkeypatch.setattr(
        utils,
        "make_test_spec",
        lambda instance: SimpleNamespace(
            image="mutable-tag",
            FAIL_TO_PASS=["assessment/tests/test_hidden.py::test_hidden"],
            PASS_TO_PASS=["tests/test_public.py::test_public", GATE_TEST],
        ),
    )

    def run(spec, prediction, client, run_id, **kwargs):
        calls.append((spec.image, prediction, run_id))
        return prediction["instance_id"], {
            prediction["instance_id"]: native
            or {"resolved": True, "patch_successfully_applied": True}
        }

    monkeypatch.setattr(run_evaluation, "run_instance", run)
    monkeypatch.setattr(validate, "read_result", lambda path: canonical)
    return calls


def test_native_grading_checks_patch_identity_and_pins_image(tmp_path, monkeypatch):
    patch = "diff --git a/a.py b/a.py\n"
    calls = mock_native_grade(
        tmp_path,
        monkeypatch,
        canonical={
            "patch_sha256": "wrong",
            "resolved": True,
        },
    )
    result = experiment.grade_trial(
        {"instance_id": "iid"},
        {"instance_id": "iid", "model_patch": patch},
        task_repo=tmp_path,
        run_id="experiment-condition",
        condition_id="model-high",
        image_id="sha256:immutable",
    )
    assert result["resolved"] is None
    assert result["status"] == "grading_error"
    assert "different patch" in result["error"]
    assert calls == [
        (
            "sha256:immutable",
            {
                "instance_id": "iid",
                "model_patch": patch,
                "model_name_or_path": "model-high",
            },
            "experiment-condition",
        )
    ]


def test_native_grading_uses_real_required_counts_not_missing_result_field(
    tmp_path, monkeypatch
):
    patch = "diff --git a/a.py b/a.py\n"
    mock_native_grade(
        tmp_path,
        monkeypatch,
        canonical={
            "patch_sha256": hashlib.sha256(patch.encode()).hexdigest(),
            "resolved": True,
            "collected": [
                "tests/test_public.py::test_public",
                "assessment/tests/test_hidden.py::test_hidden",
            ],
            "tests": {
                "tests/test_public.py::test_public": {"status": "passed"},
                "assessment/tests/test_hidden.py::test_hidden": {"status": "passed"},
            },
            "seconds": 0.1,
        },
    )
    result = experiment.grade_trial(
        {"instance_id": "iid"},
        {"instance_id": "iid", "model_patch": patch},
        task_repo=tmp_path,
        run_id="experiment-condition",
        condition_id="model-high",
        image_id="sha256:immutable",
    )
    assert result["status"] == "graded" and result["resolved"] is True
    assert result["tests_total"] == 2
    assert result["hidden_tests_total"] == 1
    assert result["tests_passed"] == 2


def test_refresh_writes_23_condition_files_and_preserves_unknown_costs(tmp_path):
    _, release = public_selection()
    tasks = [
        {
            "task_id": t["task_id"],
            "instance_id": t["instance_id"],
            "difficulty": t["design_difficulty"],
        }
        for t in release["tasks"]
    ]
    manifest = {
        "tasks": tasks,
        "conditions": experiment.conditions(),
        "run_id": "experiment",
        "release": "test",
        "release_content_sha256": "a" * 64,
        "step_limit": 50,
        "hard_timeout_seconds": 600,
        "max_output_tokens_per_request": 32768,
        "per_task_cost_limit_usd": None,
        "pricing": {},
        "expected_trials": 230,
        "smoke_task": {
            "task_id": "F01",
            "instance_id": "tsmc__f01-v0.2",
            "difficulty": "unrated",
        },
    }
    condition = manifest["conditions"][0]
    for task in tasks:
        atomic_write_json(
            experiment.trial_directory(tmp_path, condition, task) / "result.json",
            {
                **task,
                "model": condition["model"],
                "effort": condition["effort"],
                "state": "completed",
                "inference_status": "Timeout",
                "evaluation_status": "empty_submission",
                "resolved": False,
                "failure_category": "api_error",
                "estimated_cost_usd": None,
                "observed_cost_usd": 0.5,
                "cost_estimate_complete": False,
            },
        )
    overall = experiment.refresh_reports(tmp_path, manifest)
    paths = list((tmp_path / "conditions").glob("*.json"))
    assert len(paths) == 23
    for path in paths:
        report = json.loads(path.read_text())
        assert len(report["tasks"]) == 10
        assert report["summary"]["estimated_cost_usd"] is None
        assert report["summary"]["cost_estimate_complete"] is False
    report = json.loads(
        (tmp_path / "conditions" / f"{condition['condition_id']}.json").read_text()
    )
    assert report["summary"]["completed_tasks"] == 10
    assert report["summary"]["observed_cost_usd"] == 5.0
    assert report["summary"]["accuracy"] == 0.0
    assert overall["expected_trials"] == 230
    assert overall["summary"]["completed_tasks"] == 10
    assert overall["summary"]["pending_tasks"] == 220


def test_driver_lock_prevents_concurrent_paid_scheduling_and_releases_on_error(
    tmp_path,
):
    with pytest.raises(RuntimeError, match="simulated interruption"):
        with experiment.experiment_lock(tmp_path):
            with pytest.raises(ValueError, match="Another driver"):
                with experiment.experiment_lock(tmp_path):
                    pytest.fail("Second driver acquired active experiment")
            raise RuntimeError("simulated interruption")
    with experiment.experiment_lock(tmp_path):
        pass


def test_resume_cannot_attach_stale_grading_to_a_changed_patch(tmp_path, monkeypatch):
    manifest, condition, task, directory = trial_fixture(tmp_path)
    iid, patch = task["instance_id"], "changed patch"
    atomic_write_json(directory / "timing.json", {"exit_status": "Submitted"})
    atomic_write_json(
        directory / "inference" / iid / f"{iid}.traj.json",
        {"info": {"submission": patch}},
    )
    atomic_write_json(
        directory / "inference/preds.json",
        {iid: {"instance_id": iid, "model_patch": patch}},
    )
    atomic_write_json(
        directory / "evaluation.json",
        {
            "status": "graded",
            "resolved": True,
            "grading_seconds": 2.0,
            "patch_sha256": hashlib.sha256(b"old patch").hexdigest(),
        },
    )
    monkeypatch.setattr(
        experiment.timing,
        "run_instance",
        lambda *args, **kwargs: pytest.fail("Paid solver rerun"),
    )
    with pytest.raises(ValueError, match="different patch"):
        experiment.execute_trial(
            tmp_path, manifest, condition, task, {}, {}, threading.Lock()
        )
    assert not (directory / "result.json").exists()


def runnable_manifest(tmp_path, monkeypatch):
    import pyarrow as pa
    import pyarrow.parquet as pq

    rows, release = public_selection()
    tasks = [
        {
            "task_id": t["task_id"],
            "instance_id": t["instance_id"],
            "difficulty": t["design_difficulty"],
        }
        for t in release["tasks"]
    ]
    smoke = {"task_id": "F01", "instance_id": "tsmc__f01-v0.2", "difficulty": "unrated"}
    for directory, data in (
        ("public", rows),
        ("smoke-public", [{"task_id": "F01", "instance_id": smoke["instance_id"]}]),
    ):
        (tmp_path / directory).mkdir()
        pq.write_table(pa.Table.from_pylist(data), tmp_path / directory / "dev.parquet")
    manifest = {
        "tasks": tasks,
        "smoke_task": smoke,
        "conditions": experiment.conditions()[:1],
        "run_id": "test-experiment",
        "task_repo": str(tmp_path / "native"),
        "workers": 1,
        "schedule_seed": 1,
    }
    monkeypatch.setattr(
        experiment, "load_task_repo", lambda *args, **kwargs: [*tasks, smoke]
    )
    monkeypatch.setattr(experiment, "refresh_reports", lambda *args: {})
    return manifest


@pytest.mark.parametrize("gate_passes", [True, False])
def test_condition_smoke_precedes_formal_trials_without_requiring_solved_smoke(
    tmp_path, monkeypatch, gate_passes
):
    manifest = runnable_manifest(tmp_path, monkeypatch)
    events = []

    def execute(output, manifest, condition, task, row, instance, lock, *, smoke=False):
        events.append((smoke, task["task_id"]))
        return {
            "resolved": False,
            "inference_status": "Submitted",
            "usage_complete": True,
            "cost_estimate_complete": True,
            "response_count": 1 if gate_passes else 0,
            "evaluation_status": "graded",
            "patch_bytes": 100,
            "inference_seconds": 1.0,
            "grading_seconds": 2.0,
            "total_seconds": 3.0,
        }

    monkeypatch.setattr(experiment, "execute_trial", execute)
    experiment.run(tmp_path, manifest)
    assert events[0] == (True, "F01")
    if gate_passes:
        assert len(events) == 11
        assert {task for smoke, task in events[1:] if not smoke} == set(
            experiment.TASK_IDS
        )
    else:
        assert events == [(True, "F01")]


@pytest.mark.parametrize("corrupt_trajectory", [False, True])
def test_interrupted_paid_smoke_is_recorded_as_terminal_with_unknown_cost(
    tmp_path, monkeypatch, corrupt_trajectory
):
    manifest = runnable_manifest(tmp_path, monkeypatch)
    condition, task = manifest["conditions"][0], manifest["smoke_task"]
    directory = experiment.trial_directory(tmp_path, condition, task, smoke=True)
    directory.mkdir(parents=True)
    journal = directory / "requests.jsonl"
    journal.write_text(
        json.dumps(
            {"event": "request_started", "request_id": "inflight", "request_index": 1}
        )
        + "\n"
    )
    if corrupt_trajectory:
        path = directory / "inference" / task["instance_id"]
        path.mkdir(parents=True)
        (path / "task.traj.json").write_text('{"info":')
    monkeypatch.setattr(
        experiment.timing,
        "run_instance",
        lambda *args, **kwargs: pytest.fail("Paid solver rerun"),
    )
    experiment.run(tmp_path, manifest)
    result = json.loads((directory / "result.json").read_text())
    assert result["state"] == "completed"
    assert result["evaluation_status"] == "orchestration_error"
    assert result["resolved"] is None
    assert result["estimated_cost_usd"] is None
    assert result["cost_estimate_complete"] is False
    assert result["incomplete_request_count"] == 1
    experiment.run(tmp_path, manifest)
    assert json.loads((directory / "result.json").read_text()) == result
    assert not (tmp_path / "trials").exists()


def test_existing_native_report_for_another_patch_is_not_reused(tmp_path, monkeypatch):
    calls = mock_native_grade(tmp_path, monkeypatch, canonical={})
    directory = tmp_path / "same-run" / "model-high" / "iid"
    directory.mkdir(parents=True)
    (directory / "report.json").write_text("{}\n")
    (directory / "patch.diff").write_text("previous patch")
    with pytest.raises(ValueError, match="different patch"):
        experiment.grade_trial(
            {"instance_id": "iid"},
            {"instance_id": "iid", "model_patch": "new patch"},
            task_repo=tmp_path,
            run_id="same-run",
            condition_id="model-high",
            image_id="sha256:immutable",
        )
    assert calls == []
    assert (directory / "patch.diff").read_text() == "previous patch"
