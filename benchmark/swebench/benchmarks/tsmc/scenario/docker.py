"""Native task grades and fresh offline containers for candidate compositions."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import tarfile
import time

from swebench.benchmarks.tsmc.grading import evaluator
from swebench.benchmarks.tsmc.prepare import write_json
from swebench.benchmarks.tsmc.validate import checked_images, read_result
from swebench.harness.container_profiles import container_options
from swebench.harness.constants import RUN_EVALUATION_LOG_DIR
from swebench.harness.run_evaluation import _docker_client, run_instance
from swebench.harness.utils import make_test_spec

PROBE_DRIVER = """\
import json, os, subprocess, sys
from pathlib import Path
sys.path.insert(0, "/tmp/tsmc-probe")
from evaluator import check_workspace
work = Path("/testbed")
config = json.loads(Path("/tmp/tsmc-probe/config.json").read_text())
patch = Path("/tmp/tsmc-probe/candidate.patch")
subprocess.run(["git", "apply", "--check", str(patch)], cwd=work, check=True, capture_output=True, timeout=10)
subprocess.run(["git", "apply", str(patch)], cwd=work, check=True, capture_output=True, timeout=10)
check_workspace(work, config)
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=work, text=True).strip()
if head != config["base_commit"]:
    raise ValueError("Probe baseline mismatch")
env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0"}
with open("/tmp/tsmc-probe/stdout", "wb") as out, open("/tmp/tsmc-probe/stderr", "wb") as err:
    result = subprocess.run([sys.executable, "-m", "fabops", "--input", "/tmp/tsmc-probe/input.json"],
                            cwd=work, env=env, stdout=out, stderr=err, timeout=20)
output = Path("/tmp/tsmc-probe/stdout")
if result.returncode or output.stat().st_size > 1000000:
    raise ValueError("Candidate CLI failed or output exceeded 1 MB")
print(json.dumps(json.loads(output.read_text()), allow_nan=False))
"""


def archive(files):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as tar:
        for name, data in files.items():
            data = data.encode()
            info = tarfile.TarInfo("tsmc-probe/" + name)
            info.size, info.mode = len(data), 0o644
            tar.addfile(info, io.BytesIO(data))
    return stream.getvalue()


class DockerBackend:
    def __init__(self, task_repo, instances, run_id, output, configs=None):
        self.task_repo, self.instances = Path(task_repo), instances
        self.run_id, self.output = run_id, Path(output)
        self.configs = (
            configs
            if configs is not None
            else {
                sid: json.loads(
                    (
                        self.task_repo / "tasks" / row["instance_id"] / "tsmc.json"
                    ).read_text()
                )
                for sid, row in instances.items()
            }
        )
        client = _docker_client()
        try:
            images = checked_images(client, instances.values())
            self.images = {
                sid: images[row["instance_id"]] for sid, row in instances.items()
            }
        finally:
            client.close()

    def grade(self, service, patch, submitted):
        started = time.monotonic()
        instance = self.instances[service]
        sha = hashlib.sha256(patch.encode()).hexdigest()
        receipt = dict(
            service=service,
            task_id=instance["task_id"],
            instance_id=instance["instance_id"],
            attempt=1,
            patch_sha256=sha,
            base_commit=instance["base_commit"],
            image_id=self.images[service],
            resolved=False,
            queue_wall_seconds=started - submitted,
        )
        client = None
        log_dir = (
            RUN_EVALUATION_LOG_DIR / self.run_id / service / instance["instance_id"]
        )
        receipt["log_dir"] = str(log_dir.resolve())
        try:
            if (
                not patch.strip()
                or len(patch.encode()) > 4 * 1024 * 1024
                or "GIT binary patch" in patch
            ):
                raise ValueError("Empty, oversized or binary candidate patch")
            client = _docker_client()
            spec = make_test_spec(instance)
            # Use the same immutable local image for the grade and every probe.
            spec.image = self.images[service]
            prediction = dict(
                instance_id=instance["instance_id"],
                model_patch=patch,
                model_name_or_path=service,
            )
            result = run_instance(
                spec,
                prediction,
                client,
                self.run_id,
                timeout=self.configs[service]["test_timeout"] + 60,
                task_repo=str(self.task_repo),
            )
            if result is None:
                raise ValueError("Native harness produced no grade")
            detail = read_result(log_dir / "test_output.txt")
            if (
                detail.get("patch_sha256") != sha
                or detail.get("instance_id") != instance["instance_id"]
                or detail.get("base_commit") != instance["base_commit"]
            ):
                raise ValueError(
                    "Evaluator receipt does not match the submitted patch and baseline"
                )
            write_json(log_dir / "tsmc_result.json", detail)
            receipt.update(
                resolved=bool(
                    detail["resolved"]
                    and result[1][instance["instance_id"]]["resolved"]
                ),
                timeout=detail["timeout"],
                log_dir=str(log_dir.resolve()),
            )
        except Exception as exc:
            receipt["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            if client is not None:
                client.close()
        receipt["wall_seconds"] = time.monotonic() - started
        return receipt

    def invoke(self, service, patch, payload):
        client, container = _docker_client(), None
        try:
            container = client.containers.create(
                image=self.images[service],
                command=["python", "-I", "/tmp/tsmc-probe/driver.py"],
                entrypoint=[],
                working_dir="/testbed",
                platform="linux/amd64",
                **container_options("python_offline"),
            )
            container.put_archive(
                "/tmp",
                archive(
                    {
                        "driver.py": PROBE_DRIVER,
                        "evaluator.py": Path(evaluator.__file__).read_text(),
                        "config.json": json.dumps(self.configs[service]),
                        "candidate.patch": patch,
                        "input.json": json.dumps(payload, allow_nan=False),
                    }
                ),
            )
            container.start()
            result = container.wait(timeout=40)
            output = container.logs(stdout=True, stderr=False)
            if result["StatusCode"] != 0 or len(output) > 1_000_000:
                error = container.logs(stdout=False, stderr=True, tail=15).decode(
                    errors="replace"
                )
                raise ValueError(f"Candidate composition failed: {error[-4000:]}")
            return json.loads(output)
        finally:
            try:
                if container is not None:
                    container.remove(force=True)
            finally:
                client.close()
