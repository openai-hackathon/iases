"""Standalone manifest evaluator; executed in a disposable offline container.

Only canonical result lines are printed. Raw candidate output is captured and
encoded as an artifact so it cannot enter the harness's test-output parser.
The in-process pytest oracle is intended for functional evaluation, not as an
adversarial boundary against candidates deliberately attacking the test driver.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import signal
import subprocess
import sys
import time

GATE_TEST = "tsmc_grader::required_suite"
RESULT_PREFIX = "TSMC_RESULT_BASE64: "
FORBIDDEN = {"conftest.py", "sitecustomize.py", "usercustomize.py", "result_plugin.py"}


def allowed(path: str) -> bool:
    p = PurePosixPath(path)
    if p.is_absolute() or ".." in p.parts or "\\" in path or p.name in FORBIDDEN:
        return False
    return p.suffix == ".py" and (
        (len(p.parts) > 1 and p.parts[0] == "fabops")
        or (
            len(p.parts) == 2
            and p.parts[0] == "tests"
            and p.name.startswith("test_agent_")
        )
    )


def check_workspace(work: Path, config: dict) -> list[str]:
    baseline = config["public_hashes"]
    current = {}
    for path in sorted(work.rglob("*")):
        relative = path.relative_to(work)
        if ".git" in relative.parts:
            continue
        if path.is_symlink():
            raise ValueError(f"Symlink rejected: {relative}")
        if path.is_file():
            name = relative.as_posix()
            current[name] = hashlib.sha256(path.read_bytes()).hexdigest()
            if path.stat().st_mode & 0o111:
                raise ValueError(f"Executable file rejected: {name}")
    changed = sorted(
        n for n in baseline.keys() | current.keys() if baseline.get(n) != current.get(n)
    )
    illegal = [n for n in changed if not allowed(n)]
    if illegal:
        raise ValueError(f"Protected or unsupported paths changed: {illegal}")
    return changed


def validate_report(report: dict) -> None:
    """Reject malformed plugin output before copying it into a grade receipt."""
    if not isinstance(report, dict):
        raise ValueError("Pytest report must be an object")
    collected, tests = report.get("collected", []), report.get("tests", {})
    if not isinstance(collected, list) or not all(
        isinstance(n, str) for n in collected
    ):
        raise ValueError("Collected tests must be an array of names")
    if not isinstance(tests, dict) or any(
        not isinstance(name, str)
        or not isinstance(info, dict)
        or not isinstance(info.get("status"), str)
        for name, info in tests.items()
    ):
        raise ValueError("Test results must map names to status objects")
    if "exit_code" in report and type(report["exit_code"]) is not int:
        raise ValueError("Pytest exit code must be an integer")


def output_tail(path: Path, limit: int = 256_000) -> str:
    with path.open("rb") as stream:
        stream.seek(max(0, path.stat().st_size - limit))
        return stream.read(limit).decode("utf-8", errors="replace")


def suite_passed(
    report: dict, required: list[str], returncode: int, timeout: bool
) -> bool:
    try:
        validate_report(report)
    except ValueError:
        return False
    collected = report.get("collected", [])
    return bool(
        required
        and len(set(required)) == len(required)
        and len(collected) == len(required)
        and set(collected) == set(required)
        and set(report.get("tests", {})) == set(required)
        and all(report["tests"][n].get("status") == "passed" for n in required)
        and report.get("exit_code") == 0
        and returncode == 0
        and not timeout
    )


def evaluate(work: Path, assets: Path) -> dict:
    config = json.loads((assets / "config.json").read_text())
    required = config["required"]
    result = {
        "resolved": False,
        "collected": [],
        "tests": {},
        "timeout": False,
        "instance_id": config["instance_id"],
        "base_commit": config["base_commit"],
    }
    started = time.monotonic()
    try:
        patch_path = Path(config.get("candidate_patch", "/tmp/patch.diff"))
        if patch_path.exists():
            raw = patch_path.read_bytes()
            result["patch_sha256"] = hashlib.sha256(raw).hexdigest()
            if (
                len(raw) > 4 * 1024 * 1024
                or b"GIT binary patch" in raw
                or not raw.strip()
            ):
                raise ValueError("Empty, binary or oversized patch")
        result["changed_paths"] = check_workspace(work, config)
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=work,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        ).stdout.strip()
        if head != config["base_commit"]:
            raise ValueError("Baseline commit mismatch")
        # Paths protected by check_workspace still match their original hashes.
        subprocess.run(
            ["git", "apply", "--check", str(assets / "test.patch")],
            cwd=work,
            check=True,
            capture_output=True,
            timeout=10,
        )
        subprocess.run(
            ["git", "apply", str(assets / "test.patch")],
            cwd=work,
            check=True,
            capture_output=True,
            timeout=10,
        )
        output = assets / "pytest.json"
        output.unlink(missing_ok=True)
        env = {
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
            "PYTHONPATH": os.pathsep.join([str(work), str(assets)]),
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "PYTEST_ADDOPTS": "",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "TSMC_REPORT_PATH": str(output),
        }
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "result_plugin",
            "-p",
            "no:cacheprovider",
            "--import-mode=importlib",
            "tests/test_public.py",
            "assessment/tests/test_hidden.py",
        ]
        log_path = assets / "pytest.log"
        with log_path.open("wb") as log:
            process = subprocess.Popen(
                command,
                cwd=work,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            try:
                process.wait(timeout=config["test_timeout"])
            except subprocess.TimeoutExpired:
                result["timeout"] = True
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
        result.update(process_exit=process.returncode, raw_output=output_tail(log_path))
        report = (
            json.loads(output.read_text())
            if output.exists() and output.stat().st_size < 10_000_000
            else {}
        )
        validate_report(report)
        result.update(
            collected=report.get("collected", []),
            tests=report.get("tests", {}),
            pytest_exit=report.get("exit_code"),
        )
        result["resolved"] = suite_passed(
            report, required, process.returncode, result["timeout"]
        )
        if not result["resolved"]:
            result["failure_kind"] = "tests_or_execution_failed"
    except (
        ValueError,
        OSError,
        subprocess.SubprocessError,
        KeyError,
        TypeError,
    ) as exc:
        result.update(failure_kind="evaluation_rejected", error=str(exc))
    result["seconds"] = time.monotonic() - started
    result["required"] = required
    return result


def emit(result: dict) -> None:
    for node in result["required"]:
        status = (
            "PASSED"
            if result["tests"].get(node, {}).get("status") == "passed"
            else "FAILED"
        )
        print(f"{status} {node}")
    print(f"{'PASSED' if result['resolved'] else 'FAILED'} {GATE_TEST}")
    # Encoded so captured exceptions/pytest output cannot forge harness markers.
    print(RESULT_PREFIX + base64.b64encode(json.dumps(result).encode()).decode())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, default=Path("/testbed"))
    parser.add_argument("--assets", type=Path, default=Path("/opt/tsmc-grader"))
    args = parser.parse_args()
    result = evaluate(args.work.resolve(), args.assets.resolve())
    emit(result)
    raise SystemExit(0 if result["resolved"] else 1)


if __name__ == "__main__":
    main()
