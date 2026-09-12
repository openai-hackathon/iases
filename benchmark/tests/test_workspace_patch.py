"""Collect real edits without losing unstaged or newly created TSMC source."""

import json
import subprocess
from pathlib import Path

import pytest

from swebench.benchmarks.tsmc.common import git, init_git
from swebench.inference.workspace_agent import (
    collect_workspace_patch,
    workspace_agent_class,
)


class Shell:
    def __init__(self, cwd):
        self.cwd = cwd

    def execute(self, action):
        result = subprocess.run(
            action["command"],
            cwd=self.cwd,
            shell=True,
            executable="/bin/bash",
            capture_output=True,
            text=True,
            env={
                "PATH": str(Path(__import__("sys").executable).parent)
                + ":/usr/bin:/bin"
            },
        )
        return dict(returncode=result.returncode, output=result.stdout + result.stderr)


@pytest.fixture
def repository(tmp_path):
    (tmp_path / "fabops").mkdir()
    (tmp_path / "fabops/service.py").write_text("value = 1\n")
    (tmp_path / "README.md").write_text("Contract\n")
    return tmp_path, init_git(tmp_path)


def test_unstaged_and_new_files_are_collected_without_changing_real_index(repository):
    root, baseline = repository
    (root / "fabops/service.py").write_text("value = 2\n")
    (root / "fabops/new.py").write_text("result = 3\n")
    (root / "patch.txt").write_text("model-generated patch output\n")
    before = git(root, "status", "--porcelain")
    patch = collect_workspace_patch(Shell(root), baseline, ("fabops/*.py",))
    assert "+value = 2" in patch and "+result = 3" in patch
    assert "patch.txt" not in patch
    assert git(root, "status", "--porcelain") == before
    assert git(root, "diff", "--cached") == ""
    patch_path = root / "collected.patch"
    patch_path.write_text(patch)
    git(root, "reset", "--hard", baseline)
    (root / "fabops/new.py").unlink()
    git(root, "apply", "--check", str(patch_path))
    git(root, "apply", str(patch_path))
    assert (root / "fabops/service.py").read_text() == "value = 2\n"
    assert (root / "fabops/new.py").read_text() == "result = 3\n"


def test_collector_includes_committed_changes_and_protected_tracked_edits(repository):
    root, baseline = repository
    (root / "fabops/service.py").write_text("value = 2\n")
    git(root, "add", "fabops/service.py")
    git(
        root,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-qm",
        "Fixture edit",
    )
    (root / "README.md").write_text("Unauthorized contract edit\n")
    patch = collect_workspace_patch(Shell(root), baseline)
    assert "+value = 2" in patch
    assert "+Unauthorized contract edit" in patch


def test_unchanged_workspace_and_invalid_baseline(repository):
    root, baseline = repository
    assert collect_workspace_patch(Shell(root), baseline) == ""
    with pytest.raises(ValueError, match="original 40-character"):
        collect_workspace_patch(Shell(root), "HEAD; invalid")


def test_staged_new_source_is_included_for_other_repositories(repository):
    root, baseline = repository
    (root / "new_module.py").write_text("value = 42\n")
    git(root, "add", "new_module.py")
    patch = collect_workspace_patch(Shell(root), baseline)
    assert "+++ b/new_module.py" in patch and "+value = 42" in patch


@pytest.mark.parametrize("failure", [False, True])
def test_agent_preserves_original_submission_and_collects_on_model_failure(
    repository, failure
):
    root, _ = repository

    class Agent:
        env = Shell(root)
        instance_id = "tsmc__fixture-v1.0"

        def run(self, task, **kwargs):
            (root / "fabops/service.py").write_text("value = 2\n")
            if failure:
                raise TimeoutError("The model request timed out")
            return {"exit_status": "Submitted", "submission": "incorrect model output"}

        def add_messages(self, message):
            self.last_message = message

        def serialize(self, *extra_dicts):
            return {
                "info": {
                    k: v
                    for item in extra_dicts
                    for k, v in item.get("info", {}).items()
                }
            }

    agent = workspace_agent_class(Agent)()
    info = agent.run("Fix the fixture")
    assert "+value = 2" in info["submission"]
    assert info["model_submission"] == ("" if failure else "incorrect model output")
    assert info["exit_status"] == ("TimeoutError" if failure else "Submitted")
    assert agent.serialize()["info"] == {**info, "rejected_submissions": []}


def test_agent_reports_no_changes_instead_of_success(repository):
    root, _ = repository

    class Agent:
        env = Shell(root)
        instance_id = "some__repository-123"

        def run(self, task, **kwargs):
            return {"exit_status": "Submitted", "submission": ""}

        def add_messages(self, message):
            pass

    info = workspace_agent_class(Agent)().run()
    assert info["exit_status"] == "NoChanges"
    assert info["model_exit_status"] == "Submitted"
    assert info["submission"] == ""


@pytest.mark.parametrize("repair", [True, False])
@pytest.mark.parametrize("multiple_actions", [True, False])
def test_empty_submission_continues_within_original_step_budget(
    repository, repair, multiple_actions
):
    from minisweagent.agents.default import DefaultAgent
    from minisweagent.exceptions import Submitted

    root, _ = repository

    class Environment(Shell):
        def execute(self, action):
            result = super().execute(action)
            if result["output"].startswith("COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"):
                raise Submitted(
                    {
                        "role": "exit",
                        "content": "",
                        "extra": {"exit_status": "Submitted", "submission": ""},
                    }
                )
            return result

        def serialize(self):
            return {}

        def get_template_vars(self):
            return {}

    class Model:
        def query(self, messages):
            calls = sum(m["role"] == "assistant" for m in messages)
            command = "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"
            if repair and calls == 1:
                command = "printf 'value = 2\\n' > fabops/service.py"
            actions = [{"command": command}]
            if multiple_actions and (not repair or calls == 0):
                actions = [
                    {"command": "echo before"},
                    *actions,
                    {"command": "echo after"},
                ]
            return {
                "role": "assistant",
                "content": command,
                "extra": {"actions": actions},
            }

        def format_message(self, **kwargs):
            return kwargs

        def format_observation_messages(self, message, outputs, variables):
            assert len(message["extra"]["actions"]) == len(outputs)
            return [{"role": "user", "content": output["output"]} for output in outputs]

        def serialize(self):
            return {}

        def get_template_vars(self):
            return {}

    agent = workspace_agent_class(DefaultAgent)(
        Model(),
        Environment(root),
        step_limit=3,
        system_template="Repair the code using shell commands.",
        instance_template="{{task}}",
    )
    agent.instance_id = "tsmc__fixture-v1.0"
    info = agent.run("Fix the fixture")
    assert agent.n_calls == 3
    assert any("Submission rejected" in m["content"] for m in agent.messages)
    assert len(agent.rejected_submissions) == (1 if repair else 3)
    assert info["exit_status"] == ("Submitted" if repair else "LimitsExceeded")
    assert bool(info["submission"]) is repair


def test_native_tool_calls_preserve_ids_after_empty_submission(repository, monkeypatch):
    import litellm
    from minisweagent.agents.default import DefaultAgent
    from minisweagent.environments.docker import DockerEnvironment
    from minisweagent.models.litellm_model import LitellmModel

    root, baseline = repository

    class Environment(Shell):
        def execute(self, action):
            result = super().execute(action)
            result["exception_info"] = ""
            DockerEnvironment._check_finished(self, result)
            return result

        def serialize(self):
            return {}

        def get_template_vars(self):
            return {}

    commands = [
        "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT",
        "printf 'value = 2\\n' > fabops/service.py",
        "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT",
    ]
    requests = []

    def completion(**kwargs):
        messages = kwargs["messages"]
        index = len(requests)
        assert kwargs["tools"][0]["function"]["name"] == "bash"
        assert all("extra" not in message for message in messages)
        if index:
            assert messages[-1]["role"] == "tool"
            assert messages[-1]["tool_call_id"] == f"call_{index - 1}"
        if index == 1:
            assert "Submission rejected" in messages[-1]["content"]
            assert "<returncode>1</returncode>" in messages[-1]["content"]
        requests.append(messages)
        return litellm.ModelResponse(
            choices=[
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": f"call_{index}",
                                "type": "function",
                                "function": {
                                    "name": "bash",
                                    "arguments": json.dumps(
                                        {"command": commands[index]}
                                    ),
                                },
                            }
                        ],
                    },
                }
            ]
        )

    monkeypatch.setattr(litellm, "completion", completion)
    model = LitellmModel(model_name="openai/gpt-4.1")
    monkeypatch.setattr(model, "_calculate_cost", lambda response: {"cost": 0.001})
    agent = workspace_agent_class(DefaultAgent)(
        model,
        Environment(root),
        step_limit=3,
        system_template="Repair the code using the bash tool.",
        instance_template="{{task}}",
    )
    agent.instance_id = "tsmc__fixture-v1.0"

    info = agent.run("Fix the fixture")

    assert len(requests) == agent.n_calls == 3, info
    assert len(agent.rejected_submissions) == 1
    assert info["exit_status"] == "Submitted"
    assert info["model_submission"] == ""
    assert info["submission_source"] == "workspace_diff"
    assert info["patch_baseline"] == baseline
    assert "+value = 2" in info["submission"]
    assert git(root, "diff", "--cached") == ""


def test_failed_artifact_write_keeps_previous_complete_trajectory(
    tmp_path, monkeypatch
):
    from swebench.inference import workspace_agent

    path = tmp_path / "trajectory.json"
    path.write_text('{"complete": true}\n')

    def fail(value, stream, **kwargs):
        stream.write('{"incomplete":')
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(workspace_agent.json, "dump", fail)
    with pytest.raises(OSError):
        workspace_agent.atomic_write_json(path, {"next": True})
    assert path.read_text() == '{"complete": true}\n'
    assert list(tmp_path.iterdir()) == [path]
