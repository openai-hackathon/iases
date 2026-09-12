"""Collect actual workspace changes independently of the model's submitted text.

The optional runner preserves the original submission and exit status for audit.
It uses a temporary Git index, includes tracked edits and configured new Python
files, and never relies on the model remembering to stage its work.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import tempfile
from textwrap import dedent


def atomic_write_json(path, value):
    """Preserve the last complete artifact if a new write runs out of space."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def allowed_new_paths(instance_id):
    return (
        ("fabops/*.py", "tests/test_agent_*.py")
        if instance_id.startswith("tsmc__")
        else ()
    )


def collect_container_patch(container, baseline, instance_id, environment_config):
    """Recover a bounded run's files before its owned container is removed."""

    class Environment:
        def execute(self, action):
            result = container.exec_run(
                ["/bin/bash", "-c", action["command"]],
                workdir=environment_config.get("cwd", "/testbed"),
                environment=environment_config.get("env", {}),
            )
            return {"returncode": result.exit_code, "output": result.output.decode()}

    return collect_workspace_patch(
        Environment(), baseline, allowed_new_paths(instance_id)
    )


def collect_workspace_patch(environment, baseline: str, new_paths=()):
    if not re.fullmatch(r"[0-9a-f]{40}", baseline):
        raise ValueError("Expected the original 40-character Git commit")
    script = (
        dedent("""
        import fnmatch
        import os
        from pathlib import Path
        import subprocess
        import tempfile
        BASELINE = __BASELINE__
        NEW_PATHS = __NEW_PATHS__
        git = ["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false"]
        tracked = set(subprocess.run(git + ["ls-files", "-z"], check=True,
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode().split("\\0"))
        with tempfile.TemporaryDirectory(prefix="swebench-patch-") as temporary:
            env = dict(os.environ, GIT_INDEX_FILE=str(Path(temporary) / "index"))
            def command(*args):
                return subprocess.run([*git, *args], env=env, check=True,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
            command("read-tree", "HEAD")
            command("add", "-u", "--", ".")
            untracked = command("ls-files", "--others", "--exclude-standard", "-z").decode().split("\\0")
            selected = [name for name in untracked if name and (name in tracked or
                        (Path(name).is_file() and not Path(name).is_symlink()
                         and any(fnmatch.fnmatchcase(name, pattern) for pattern in NEW_PATHS)))]
            if selected:
                command("add", "-N", "--", *selected)
            patch = command("diff", "--no-ext-diff", "--no-textconv", "--binary", BASELINE, "--", ".")
            print(patch.decode(), end="")
    """)
        .replace("__BASELINE__", repr(baseline))
        .replace("__NEW_PATHS__", repr(tuple(new_paths)))
    )
    result = environment.execute(
        {
            "command": "python -I - <<'SWEBENCH_COLLECT_PATCH'\n"
            + script
            + "\nSWEBENCH_COLLECT_PATCH"
        }
    )
    if result.get("returncode") != 0:
        raise ValueError(
            "Workspace patch collection failed: " + result.get("output", "")[-1000:]
        )
    return result["output"]


def workspace_agent_class(base_class):
    """Wrap mini's agent while keeping its optional dependency out of imports."""

    class WorkspaceAgent(base_class):
        def execute_actions(self, message):
            from minisweagent.exceptions import Submitted

            outputs = []
            for action in message.get("extra", {}).get("actions", []):
                try:
                    outputs.append(self.env.execute(action))
                except Submitted as exc:
                    patch = collect_workspace_patch(
                        self.env,
                        self.patch_baseline,
                        allowed_new_paths(self.instance_id),
                    )
                    if patch.strip():
                        raise
                    self.rejected_submissions.extend(exc.messages)
                    outputs.append(
                        {
                            "returncode": 1,
                            "exception_info": "",
                            "output": (
                                "Submission rejected: the workspace has no code changes against "
                                "the original commit. Inspect the existing implementation, "
                                "reproduce the issue, edit the source files, and run relevant "
                                "tests before submitting again. Your existing step and time "
                                "budgets still apply."
                            ),
                        }
                    )
            return self.add_messages(
                *self.model.format_observation_messages(
                    message, outputs, self.get_template_vars()
                )
            )

        def run(self, task="", **kwargs):
            self.workspace_info = {}
            self.rejected_submissions = []
            original = self.env.execute({"command": "git rev-parse HEAD"})
            if original.get("returncode") != 0:
                raise ValueError("Cannot capture the original workspace commit")
            baseline = original["output"].strip()
            self.patch_baseline = baseline
            try:
                info = super().run(task, **kwargs)
            except Exception as exc:
                info = dict(
                    exit_status=type(exc).__name__,
                    submission="",
                    exception_str=str(exc),
                )
            info = dict(info)
            info["model_exit_status"] = info.get("exit_status")
            info["model_submission"] = info.get("submission") or ""
            info["patch_baseline"] = baseline
            # Include all tracked edits and explicitly allowed new TSMC files.
            # Other repositories can stage new files to include them.
            new_paths = allowed_new_paths(self.instance_id)
            try:
                info["submission"] = collect_workspace_patch(
                    self.env, baseline, new_paths
                )
                info["submission_source"] = "workspace_diff"
                if (
                    not info["submission"].strip()
                    and info["exit_status"] == "Submitted"
                ):
                    info["exit_status"] = "NoChanges"
            except ValueError as exc:
                info.update(
                    exit_status="PatchCollectionError",
                    submission="",
                    patch_collection_error=str(exc),
                )
            self.workspace_info = info
            self.add_messages(
                {"role": "exit", "content": info["exit_status"], "extra": info}
            )
            return info

        def serialize(self, *extra_dicts):
            return super().serialize(
                {
                    "info": {
                        **getattr(self, "workspace_info", {}),
                        "rejected_submissions": getattr(
                            self, "rejected_submissions", []
                        ),
                    }
                },
                *extra_dicts,
            )

        def save(self, path, *extra_dicts):
            data = self.serialize(*extra_dicts)
            if path:
                atomic_write_json(path, data)
            return data

    return WorkspaceAgent


def main():
    from minisweagent.run.benchmarks import swebench as runner
    from minisweagent.run.benchmarks.utils.common import ProgressTrackingAgent

    runner.ProgressTrackingAgent = workspace_agent_class(ProgressTrackingAgent)
    runner.app()


if __name__ == "__main__":
    main()
