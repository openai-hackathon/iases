"""Reproducible public workspaces and source validation."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess

BASELINE_DATE = "2026-09-12T00:00:00Z"
BASELINE_MESSAGE = "Task baseline; no solution history"
IGNORED = {".git", "__pycache__", ".pytest_cache"}


def task_id(value: str) -> str:
    value = value.upper()
    if not re.fullmatch(r"[FAR][0-9]{2}", value):
        raise ValueError(f"Invalid task ID: {value}")
    return value


def instance_id(task: str, version: str = "0.2") -> str:
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)*", version):
        raise ValueError(f"Invalid task version: {version}")
    return f"tsmc__{task_id(task).lower()}-v{version}"


def file_hashes(root: Path) -> dict[str, str]:
    result = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in IGNORED for part in relative.parts) or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            raise ValueError(f"Symlink in source: {path}")
        if path.is_file():
            result[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def copy_tree(source: Path, target: Path) -> None:
    file_hashes(source)  # refuse symlinks before copying anything
    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns(*IGNORED, "*.pyc"),
    )


def git(work: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_AUTHOR_DATE=BASELINE_DATE,
        GIT_COMMITTER_DATE=BASELINE_DATE,
    )
    return subprocess.run(
        [
            "git",
            "-c",
            "core.autocrlf=false",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "commit.gpgsign=false",
            "-C",
            str(work),
            *args,
        ],
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout


def init_git(work: Path) -> str:
    git(work, "init", "-q", "--initial-branch=main", "--object-format=sha1")
    git(work, "config", "user.name", "TSMC-bench fixture")
    git(work, "config", "user.email", "fixture@example.invalid")
    git(work, "add", ".")
    git(work, "commit", "-qm", BASELINE_MESSAGE)
    return git(work, "rev-parse", "HEAD").strip()
