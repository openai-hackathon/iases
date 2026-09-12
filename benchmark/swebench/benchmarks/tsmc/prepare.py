"""Compile author fixtures into a native task repo and public inference data."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import shutil
import tempfile

from swebench.benchmarks.tsmc import DATASET, GATE_TEST
from swebench.benchmarks.tsmc import common
from swebench.benchmarks.tsmc.common import (
    copy_tree,
    file_hashes,
    git,
    init_git,
    instance_id,
    task_id,
)
from swebench.task.checks import check_task_repo, errors, expected_image
from swebench.task.repo import dump_yaml

# The linux/amd64 manifest, not a floating Python tag.
BASE_IMAGE = "python:3.13.9-slim-bookworm@sha256:8cdd496996889eef0a8a7921c152c0a4a9f18a26c7a5e7257d3c90b431891894"
REQUIREMENTS = "pytest==9.0.2\niniconfig==2.3.0\npackaging==25.0\npluggy==1.6.0\nPygments==2.19.2\n"
GENERATOR = "swebench.tsmc.prepare"
SPLITS = ("demo_dev", "dev", "test")


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )


def eval_script(config: dict, test_patch: str) -> str:
    grading = Path(__file__).parent / "grading"
    payload = {"config.json": json.dumps(config), "test.patch": test_patch}
    payload.update(
        {
            name: (grading / name).read_text()
            for name in ("evaluator.py", "result_plugin.py")
        }
    )
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    # Disable shell tracing before writing any material containing marker text.
    return (
        "#!/bin/bash\nset -uxo pipefail\nset +x\n"
        "cd /testbed || exit 1\n"
        "python -I - <<'TSMC_ASSETS' || exit 1\n"
        "import base64,json\nfrom pathlib import Path\n"
        "root=Path('/opt/tsmc-grader');root.mkdir(parents=True,exist_ok=True)\n"
        f"files=json.loads(base64.b64decode({encoded!r}))\n"
        "for name,content in files.items(): (root/name).write_text(content)\n"
        "TSMC_ASSETS\n"
        "echo '>>>>> Start Test Output'\n"
        "python -I /opt/tsmc-grader/evaluator.py\n"
        "echo '>>>>> End Test Output'\n"
    )


def dockerfile(commit: str) -> str:
    return f"""FROM {BASE_IMAGE}
RUN apt-get update && apt-get install -y --no-install-recommends git patch ca-certificates && rm -rf /var/lib/apt/lists/*
COPY requirements-eval.txt /opt/requirements-eval.txt
RUN python -m pip install --no-cache-dir -r /opt/requirements-eval.txt
ENV PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONHASHSEED=0
COPY workspace/ /testbed/
COPY bootstrap.py /opt/tsmc-bootstrap.py
WORKDIR /testbed
RUN python -I /opt/tsmc-bootstrap.py /testbed {commit}
LABEL org.tsmc-bench.synthetic="true" org.tsmc-bench.base-commit="{commit}"
CMD ["/bin/bash"]
"""


def prepare_task(source: Path, target: Path, test_timeout: float) -> tuple[dict, dict]:
    metadata = json.loads((source / "task.json").read_text())
    split = metadata["split"]
    if split not in SPLITS:
        raise ValueError(f"Unsupported task split: {split}")
    task = task_id(metadata["task_id"])
    iid = instance_id(task, metadata["version"])
    hashes = file_hashes(source / "agent")
    if hashes != metadata["agent_file_sha256"]:
        raise ValueError(f"{task}: public source hashes differ from task.json")
    manifest = json.loads((source / "author/tests_manifest.json").read_text())
    f2p, p2p, required = (
        manifest[k] for k in ("FAIL_TO_PASS", "PASS_TO_PASS", "required")
    )
    if (
        not f2p
        or not p2p
        or set(f2p) & set(p2p)
        or set(f2p + p2p) != set(required)
        or len(set(required)) != len(required)
        or len(f2p + p2p) != len(required)
    ):
        raise ValueError(f"{task}: invalid test partition")
    gold = (source / "author/gold.patch").read_text()
    target.mkdir(parents=True)
    copy_tree(source / "agent", target / "workspace")
    variants = {}
    with tempfile.TemporaryDirectory(prefix="tsmc-compile-") as temporary:
        work = Path(temporary) / "workspace"
        copy_tree(source / "agent", work)
        commit = init_git(work)
        git(work, "apply", "--check", str((source / "author/gold.patch").resolve()))
        copy_tree(source / "author/tests", work / "assessment/tests")
        copy_tree(source / "author/data", work / "assessment/data")
        git(work, "add", "-N", "assessment")
        test_patch = git(work, "diff", "--binary", "--", "assessment")
        if not test_patch:
            raise ValueError(f"{task}: no private tests")
    for mutant in sorted((source / "author/mutants").iterdir()):
        if not mutant.is_dir():
            continue
        with tempfile.TemporaryDirectory(prefix="tsmc-mutant-") as temporary:
            work = Path(temporary) / "workspace"
            copy_tree(source / "agent", work)
            init_git(work)
            for name in file_hashes(mutant):
                path = work / name
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(mutant / name, path)
            git(work, "add", "-A")
            variants["mutant_" + mutant.name] = git(
                work, "diff", "--cached", "--binary"
            )
    for name, patch in variants.items():
        (target / "variants").mkdir(exist_ok=True)
        (target / "variants" / f"{name}.patch").write_text(patch)
    spec = dict(
        instance_id=iid,
        repo=f"tsmc/{task.lower()}",
        version=metadata["version"],
        base_commit=commit,
        split=split,
        datasets=[DATASET],
        image=expected_image(iid),
        log_parser="parse_log_pytest_v2",
        eval_type="pass_and_fail",
        container_profile="python_offline",
        task_id=task,
        synthetic=True,
        created_at="2026-09-12T00:00:00Z",
        source_manifest_sha256=hashlib.sha256(
            (source / "task.json").read_bytes()
        ).hexdigest(),
    )
    config = dict(
        instance_id=iid,
        base_commit=commit,
        public_hashes=hashes,
        required=required,
        test_timeout=test_timeout,
    )
    (target / "task.yaml").write_text(dump_yaml(spec))
    write_json(
        target / "tests.json", {"FAIL_TO_PASS": [*f2p, GATE_TEST], "PASS_TO_PASS": p2p}
    )
    write_json(
        target / "tsmc.json",
        {
            **config,
            "task_id": task,
            "FAIL_TO_PASS": f2p,
            "PASS_TO_PASS": p2p,
            "variants": list(variants),
        },
    )
    (target / "problem_statement.md").write_text(
        (source / "agent/problem_statement.md").read_text()
    )
    (target / "gold.patch").write_text(gold)
    (target / "test.patch").write_text(test_patch)
    (target / "eval.sh").write_text(eval_script(config, test_patch))
    (target / "Dockerfile").write_text(dockerfile(commit))
    (target / "requirements-eval.txt").write_text(REQUIREMENTS)
    (target / "bootstrap.py").write_text(
        Path(common.__file__).read_text()
        + "\nif __name__ == '__main__':\n    import sys\n    assert init_git(Path(sys.argv[1])) == sys.argv[2], 'Baseline commit mismatch'\n"
    )
    (target / ".dockerignore").write_text(
        "**\n!workspace/\n!workspace/**\n!bootstrap.py\n!requirements-eval.txt\n!Dockerfile\n!.dockerignore\n"
    )
    public = {
        k: spec[k] for k in ("instance_id", "repo", "version", "base_commit", "task_id")
    }
    public.update(
        image_name=spec["image"],
        problem_statement=(target / "problem_statement.md").read_text(),
    )
    return spec, public


def prepare(
    source: Path,
    output: Path,
    tasks: list[str] | None = None,
    test_timeout: float = 45,
    export_test: bool = False,
) -> dict:
    source, output = source.resolve(), output.resolve()
    if not math.isfinite(test_timeout) or test_timeout <= 0:
        raise ValueError("test_timeout must be positive")
    if source == output or source in output.parents or output in source.parents:
        raise ValueError("Source and generated output must not overlap")
    if output.exists() and any(output.iterdir()):
        marker = output / "tsmc-generated.json"
        if (
            not marker.is_file()
            or json.loads(marker.read_text()).get("generator") != GENERATOR
        ):
            raise ValueError(
                f"Refusing to replace a directory not generated by {GENERATOR}: {output}"
            )
    available = {
        p.name: p for p in (source / "tasks").iterdir() if (p / "task.json").is_file()
    }
    selected = sorted({task_id(t) for t in tasks} if tasks else available)
    if not selected or set(selected) - available.keys():
        raise ValueError(f"Unknown or empty task selection: {selected}")
    from swebench.benchmarks.tsmc.release import verify_release

    release = verify_release(source)
    split_by_task = {
        task: json.loads((available[task] / "task.json").read_text())["split"]
        for task in selected
    }
    if set(split_by_task.values()) - set(SPLITS):
        raise ValueError("Unsupported task split")
    splits = [split for split in SPLITS if split in split_by_task.values()]
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".tsmc-prepare-", dir=output.parent
    ) as temporary:
        root = Path(temporary) / "generated"
        task_repo = root / "task-repo"
        task_repo.mkdir(parents=True)
        (task_repo / "sweb.yaml").write_text(
            dump_yaml({"datasets": [DATASET], "splits": splits})
        )
        public = {split: [] for split in splits}
        for task in selected:
            meta = json.loads((available[task] / "task.json").read_text())
            _, row = prepare_task(
                available[task],
                task_repo / "tasks" / instance_id(task, meta["version"]),
                test_timeout,
            )
            public[split_by_task[task]].append(row)
        problems = errors(check_task_repo(task_repo))
        if problems:
            raise ValueError("\n".join(map(str, problems)))
        from datasets import Dataset

        for directory, exported in (
            ("public", [s for s in splits if s != "test"]),
            ("heldout-public", ["test"] if export_test and "test" in splits else []),
        ):
            if not exported:
                continue
            public_dir = root / directory
            public_dir.mkdir()
            for split in exported:
                Dataset.from_list(public[split]).to_parquet(
                    str(public_dir / f"{split}.parquet")
                )
            fingerprint = hashlib.sha256(
                json.dumps(file_hashes(public_dir), sort_keys=True).encode()
            ).hexdigest()[:16]
            metadata = {
                "configs": [
                    {
                        "config_name": f"tsmc-{fingerprint}",
                        "data_files": [
                            {"split": s, "path": f"{s}.parquet"} for s in exported
                        ],
                    }
                ]
            }
            (public_dir / "README.md").write_text(
                "---\n"
                + dump_yaml(metadata)
                + "---\nSynthetic manufacturing repair tasks.\n"
                "This solver export contains no reference patches or private tests.\n"
            )
        result = dict(
            generator=GENERATOR,
            schema_version=2,
            dataset=DATASET,
            split=splits[0] if len(splits) == 1 else "all",
            splits=splits,
            heldout_exported=export_test and "test" in splits,
            tasks=selected,
            source_hashes=release["files"] if release else file_hashes(source),
            release_sha256=release["content_sha256"] if release else None,
            base_image=BASE_IMAGE,
        )
        write_json(root / "tsmc-generated.json", result)
        # Only replace outputs carrying our marker, after the new tree validates.
        if output.exists():
            output.rename(Path(temporary) / "previous")
        root.rename(output)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("benchmarks/tsmc"))
    parser.add_argument("--output", type=Path, default=Path(".generated/tsmc"))
    parser.add_argument(
        "--task", action="append", help="Task ID; repeat to select a subset"
    )
    parser.add_argument("--test-timeout", type=float, default=45)
    parser.add_argument(
        "--export-test",
        action="store_true",
        help="Explicitly create a separate heldout-public/test.parquet solver export",
    )
    args = parser.parse_args()
    try:
        result = prepare(
            args.source, args.output, args.task, args.test_timeout, args.export_test
        )
    except (ValueError, OSError) as exc:
        parser.exit(1, f"error: {exc}\n")
    print(f"Prepared {len(result['tasks'])} tasks in {args.output.resolve()}")


if __name__ == "__main__":
    main()
