"""The timing wrapper owns its timeout and cleans up only its trial's containers."""

import json
from pathlib import Path
import signal
import subprocess
from types import SimpleNamespace
import pytest

from swebench.benchmarks.tsmc import timing


def test_provider_overlay_preserves_native_tools_and_omits_provider_extras(tmp_path):
    agent = tmp_path / "agent.yaml"
    agent.write_text(
        "agent:\n  cost_limit: 3\n  step_limit: 100\n"
        "run:\n  collect_workspace: true\n"
        "environment:\n  environment_class: docker\n"
    )
    provider = tmp_path / "provider.yaml"
    provider.write_text(
        "model:\n  model_name: openai/example-model\n  model_class: litellm\n"
        "  model_kwargs:\n    max_completion_tokens: 4096\n"
    )
    config = timing.prepare_config([agent, provider], steps=50, timeout=600)
    assert config["agent"] == {
        "cost_limit": 3,
        "step_limit": 50,
        "wall_time_limit_seconds": 600,
    }
    assert config["run"]["collect_workspace"] is True
    assert config["environment"]["environment_class"] == "docker"
    assert config["model"] == {
        "model_name": "openai/example-model",
        "model_class": "litellm",
        "model_kwargs": {"max_completion_tokens": 4096},
    }


@pytest.mark.parametrize("suffix", ["", "/", "/v1", "/v1/"])
def test_explicit_endpoint_preserves_text_model_configuration(tmp_path, suffix):
    path = tmp_path / "provider.yaml"
    path.write_text(
        "model:\n  model_name: openai/local\n  model_class: litellm_textbased\n"
        "  model_kwargs:\n    api_key: x\n"
        "    extra_body:\n      priority: 0\n"
    )
    config = timing.prepare_config(
        [path], steps=50, timeout=600, endpoint="https://example.test" + suffix
    )
    assert config["model"]["model_class"] == "litellm_textbased"
    assert config["model"]["model_kwargs"] == {
        "api_base": "https://example.test/v1",
        "api_key": "x",
        "extra_body": {"priority": 0},
    }


@pytest.mark.parametrize("model_seed", [None, 77])
def test_timing_cli_separates_sampling_seed_from_api_seed(
    tmp_path, monkeypatch, model_seed
):
    import pyarrow as pa
    import pyarrow.parquet as parquet

    dataset = tmp_path / "dataset"
    dataset.mkdir()
    parquet.write_table(
        pa.Table.from_pylist([{"instance_id": "tsmc__f01-v0.2"}]),
        dataset / "demo_dev.parquet",
    )
    agent, provider = tmp_path / "agent.yaml", tmp_path / "provider.yaml"
    agent.write_text("run:\n  collect_workspace: true\n")
    provider.write_text("model:\n  model_class: litellm\n")
    output = tmp_path / "output"
    argv = [
        "timing",
        "--dataset",
        str(dataset),
        "--config",
        str(agent),
        "--config",
        str(provider),
        "--output",
        str(output),
        "--model",
        "openai/example-model",
        "--count",
        "1",
        "--workers",
        "1",
        "--rounds",
        "2",
        "--seed",
        "42",
        "--min-free-mb",
        "0",
    ]
    if model_seed is not None:
        argv.extend(["--model-seed", str(model_seed)])
    observed = []

    def run(row, directory, config, dataset, split, limit):
        observed.append(json.loads(json.dumps(config)))
        return {"instance_id": row["instance_id"]}

    monkeypatch.setattr(timing.sys, "argv", argv)
    monkeypatch.setattr(timing, "run_instance", run)
    timing.main()
    assert len(observed) == 2
    for index, config in enumerate(observed):
        assert config["run"]["collect_workspace"] is True
        assert config["model"]["model_name"] == "openai/example-model"
        assert config["model"]["model_class"] == "litellm"
        kwargs = config["model"]["model_kwargs"]
        assert "api_base" not in kwargs and "extra_body" not in kwargs
        if model_seed is None:
            assert "seed" not in kwargs
        else:
            assert kwargs["seed"] == model_seed + index
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["seed"] == 42
    assert manifest["model_seed"] == model_seed
    assert manifest["endpoint"] is None


def test_invalid_provider_config_fails_before_creating_artifacts(tmp_path, monkeypatch):
    config = tmp_path / "config.yaml"
    config.write_text("model:\n  model_kwargs:\n    fallbacks: []\n")
    output = tmp_path / "output"
    monkeypatch.setattr(
        timing.sys,
        "argv",
        [
            "timing",
            "--dataset",
            str(tmp_path / "missing-dataset"),
            "--config",
            str(config),
            "--output",
            str(output),
        ],
    )
    with pytest.raises(SystemExit) as exc:
        timing.main()
    assert exc.value.code == 2
    assert not output.exists()


def test_disk_preflight_rejects_low_space_before_inference(tmp_path, monkeypatch):
    monkeypatch.setattr(
        timing.shutil, "disk_usage", lambda path: SimpleNamespace(free=100)
    )
    with pytest.raises(ValueError, match="Insufficient disk space"):
        timing.check_disk_space(tmp_path / "new-run", 101)
    timing.check_disk_space(tmp_path / "new-run", 100)


@pytest.mark.parametrize("already_exited", [False, True])
def test_hard_timeout_terminates_owned_process_and_filters_container_cleanup(
    tmp_path, monkeypatch, already_exited
):
    import docker

    killed, filters, removed, waits = [], [], [], []

    class Process:
        pid = 987654

        def wait(self, timeout=None):
            waits.append(timeout)
            if len(waits) == 1:
                raise subprocess.TimeoutExpired("owned-inference", timeout)
            return -signal.SIGTERM

    def containers(**kwargs):
        filters.append(kwargs)
        return [SimpleNamespace(remove=lambda **kw: removed.append(kw))]

    def killpg(pid, sig):
        killed.append((pid, sig))
        if already_exited:
            raise ProcessLookupError("Child exited just before termination")

    monkeypatch.setattr(timing.subprocess, "Popen", lambda *a, **kw: Process())
    monkeypatch.setattr(timing.os, "killpg", killpg)
    monkeypatch.setattr(
        docker,
        "from_env",
        lambda **kwargs: SimpleNamespace(
            containers=SimpleNamespace(list=containers), close=lambda: None
        ),
    )
    result = timing.run_instance(
        {"instance_id": "tsmc__f01-v0.2"},
        tmp_path / "trial",
        {"environment": {}},
        tmp_path / "public",
        "demo_dev",
        0.01,
    )
    assert result["hard_timeout"] and result["exit_status"] == "HardTimeout"
    assert waits == [0.01, 3]
    assert killed == [(987654, signal.SIGTERM)]
    assert result["subprocess_return_code"] == -signal.SIGTERM
    assert filters[0]["filters"]["label"].startswith("tsmc-bench.timing=")
    assert removed == [{"force": True}]
    assert json.loads((tmp_path / "trial/timing.json").read_text())["hard_timeout"]


def test_successful_timing_preserves_exit_status_and_step_count(tmp_path, monkeypatch):
    import docker

    def popen(command, **kwargs):
        output = Path(command[command.index("-o") + 1]) / "tsmc__f01-v0.2"
        output.mkdir(parents=True)
        (output / "task.traj.json").write_text(
            json.dumps(
                {
                    "info": {
                        "exit_status": "LimitsExceeded",
                        "submission": "",
                        "model_stats": {"api_calls": 50, "instance_cost": 17.25},
                    }
                }
            )
        )
        return SimpleNamespace(wait=lambda **kwargs: 0)

    monkeypatch.setattr(timing.subprocess, "Popen", popen)
    monkeypatch.setattr(
        docker,
        "from_env",
        lambda **kwargs: SimpleNamespace(
            containers=SimpleNamespace(list=lambda **kwargs: []), close=lambda: None
        ),
    )
    result = timing.run_instance(
        {"instance_id": "tsmc__f01-v0.2"},
        tmp_path / "trial",
        {"environment": {}},
        tmp_path / "public",
        "demo_dev",
        600,
    )
    assert result["exit_status"] == "LimitsExceeded"
    assert result["api_calls"] == 50 and not result["hard_timeout"]
    assert result["subprocess_return_code"] == 0
    assert result["model_stats"] == {"api_calls": 50, "instance_cost": 17.25}
    assert Path(result["trajectory_path"]).is_file()
    assert result["prediction_path"] is None
    assert result["inference_ended_at"] <= result["ended_at"]
    assert result["cleanup_seconds"] >= 0


def test_hard_timeout_recovers_changes_before_removing_workspace(tmp_path, monkeypatch):
    import docker
    from swebench.inference import workspace_agent

    events = []

    class Process:
        pid = 987654
        stopped = False

        def wait(self, timeout=None):
            if not self.stopped:
                self.stopped = True
                raise subprocess.TimeoutExpired("owned-inference", timeout)
            return -signal.SIGTERM

    container = SimpleNamespace(remove=lambda **kw: events.append("remove"))

    def collect(actual, baseline, instance_id, config):
        assert actual is container and baseline == "a" * 40
        events.append("collect")
        return "diff --git a/code.py b/code.py\n"

    monkeypatch.setattr(workspace_agent, "collect_container_patch", collect)
    monkeypatch.setattr(timing.subprocess, "Popen", lambda *a, **kw: Process())
    monkeypatch.setattr(timing.os, "killpg", lambda *args: events.append("stop"))
    monkeypatch.setattr(
        docker,
        "from_env",
        lambda **kw: SimpleNamespace(
            containers=SimpleNamespace(list=lambda **kw: [container]),
            close=lambda: None,
        ),
    )
    result = timing.run_instance(
        {"instance_id": "some__repository-123", "base_commit": "a" * 40},
        tmp_path / "trial",
        {"environment": {}, "run": {"collect_workspace": True}},
        tmp_path / "public",
        "dev",
        0.01,
    )
    assert events == ["stop", "collect", "remove"]
    assert result["exit_status"] == "HardTimeout" and result["nonempty_submission"]
    assert result["api_calls"] is None and result["patch_collection_error"] is None
    prediction = json.loads((tmp_path / "trial/inference/preds.json").read_text())
    assert prediction["some__repository-123"]["model_patch"].startswith("diff --git")
    assert Path(result["trajectory_path"]).is_file()
    assert Path(result["prediction_path"]).is_file()


def test_invalid_trajectory_still_cleans_up_owned_container(tmp_path, monkeypatch):
    import docker

    removed = []

    def popen(command, **kwargs):
        output = Path(command[command.index("-o") + 1]) / "some__repository-123"
        output.mkdir(parents=True)
        (output / "task.traj.json").write_text('{"info":')
        return SimpleNamespace(wait=lambda **kwargs: 1)

    monkeypatch.setattr(timing.subprocess, "Popen", popen)
    monkeypatch.setattr(
        docker,
        "from_env",
        lambda **kw: SimpleNamespace(
            containers=SimpleNamespace(
                list=lambda **kw: [
                    SimpleNamespace(remove=lambda **kw: removed.append(True))
                ]
            ),
            close=lambda: None,
        ),
    )
    result = timing.run_instance(
        {"instance_id": "some__repository-123"},
        tmp_path / "trial",
        {"environment": {}},
        tmp_path / "public",
        "dev",
        600,
    )
    assert removed == [True]
    assert result["exit_status"] == "InvalidTrajectory"
    assert result["trajectory_error"] and not result["nonempty_submission"]


def test_process_start_failure_is_recorded_without_reusing_trial(tmp_path, monkeypatch):
    import docker

    attempts = []

    def popen(command, **kwargs):
        attempts.append(command)
        raise OSError("Unable to start worker")

    monkeypatch.setattr(timing.subprocess, "Popen", popen)
    monkeypatch.setattr(
        docker,
        "from_env",
        lambda **kwargs: SimpleNamespace(
            containers=SimpleNamespace(list=lambda **kwargs: []), close=lambda: None
        ),
    )
    arguments = (
        {"instance_id": "tsmc__f01-v0.2"},
        tmp_path / "trial",
        {"environment": {}},
        tmp_path / "public",
        "demo_dev",
        600,
    )
    result = timing.run_instance(*arguments, retry_attempts=1)
    assert result["exit_status"] == "ProcessError"
    assert "Unable to start worker" in result["process_error"]
    assert result["model_stats"] == {} and result["api_calls"] is None
    assert result["trajectory_path"] is None and result["prediction_path"] is None
    assert json.loads((tmp_path / "trial/timing.json").read_text()) == result
    with pytest.raises(FileExistsError):
        timing.run_instance(*arguments, retry_attempts=1)
    assert len(attempts) == 1


def test_trial_overrides_retries_and_journal_without_mutating_config(
    tmp_path, monkeypatch
):
    import docker

    calls = []

    def popen(command, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(wait=lambda **kwargs: 1)

    monkeypatch.setattr(timing.subprocess, "Popen", popen)
    monkeypatch.setattr(
        docker,
        "from_env",
        lambda **kwargs: SimpleNamespace(
            containers=SimpleNamespace(list=lambda **kwargs: []), close=lambda: None
        ),
    )
    config = {"environment": {}, "model": {"model_name": "example"}}
    journal = tmp_path / "trial/requests.jsonl"
    result = timing.run_instance(
        {"instance_id": "tsmc__f01-v0.2"},
        tmp_path / "trial",
        config,
        tmp_path / "public",
        "demo_dev",
        600,
        retry_attempts=1,
        request_log_path=journal,
    )
    assert calls[0]["env"]["MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT"] == "1"
    actual = timing.load_yaml(tmp_path / "trial/config.yaml")
    assert actual["model"]["request_log_path"] == str(journal.resolve())
    assert result["request_log_path"] == str(journal.resolve())
    assert result["model_retry_attempts"] == 1
    assert config == {"environment": {}, "model": {"model_name": "example"}}


def test_one_cleanup_failure_does_not_skip_other_owned_containers(
    tmp_path, monkeypatch
):
    import docker

    removed = []

    def remove_first(**kwargs):
        removed.append("first")
        raise OSError("First container could not be removed")

    containers = [
        SimpleNamespace(remove=remove_first),
        SimpleNamespace(remove=lambda **kwargs: removed.append("second")),
    ]
    monkeypatch.setattr(
        timing.subprocess,
        "Popen",
        lambda *args, **kwargs: SimpleNamespace(wait=lambda **kwargs: 1),
    )
    monkeypatch.setattr(
        docker,
        "from_env",
        lambda **kwargs: SimpleNamespace(
            containers=SimpleNamespace(list=lambda **kwargs: containers),
            close=lambda: removed.append("closed"),
        ),
    )
    result = timing.run_instance(
        {"instance_id": "tsmc__f01-v0.2"},
        tmp_path / "trial",
        {"environment": {}},
        tmp_path / "public",
        "demo_dev",
        600,
    )
    assert removed == ["first", "second", "closed"]
    assert result["cleanup_errors"] == ["First container could not be removed"]
