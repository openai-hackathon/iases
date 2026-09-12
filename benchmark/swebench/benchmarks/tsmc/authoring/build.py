"""Build trusted authored tasks, deriving test partitions from actual executions.

Author code and references execute here. Submitted model code is never an input
to this tool and must only execute inside the evaluation harness's containers.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from swebench.benchmarks.tsmc.common import copy_tree, file_hashes, git, init_git
from swebench.benchmarks.tsmc.prepare import REQUIREMENTS, write_json
from .schema import Task, code

DEV_TASKS = {
    "F05",
    "R07",
    "A05",
    "A06",
    "R05",
    "R06",
    "F11",
    "F12",
    "A11",
    "A12",
    "A13",
    "R11",
    "A19",
    "R13",
    "F19",
    "F20",
    "A20",
    "A21",
    "A22",
    "R21",
    "R29",
    "F25",
    "A29",
}

CLI = code('''
    """Run a deterministic synthetic manufacturing request."""
    import argparse
    import json
    from pathlib import Path
    from .domain import run

    def main():
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--input", required=True)
        args = parser.parse_args()
        request = json.loads(Path(args.input).read_text())
        print(json.dumps(run(request), sort_keys=True, allow_nan=False))

    if __name__ == "__main__":
        main()
''')

CLI_TEST = code("""
    def test_public_cli_fixture():
        import json
        from pathlib import Path
        import subprocess
        import sys
        completed = subprocess.run(
            [sys.executable, "-m", "fabops", "--input", "data/request.json"],
            capture_output=True, text=True, timeout=10, check=True)
        assert json.loads(completed.stdout) == json.loads(Path("data/expected.json").read_text())
""")


def tests(cases, extra):
    text = "import copy\nimport pytest\nfrom fabops.domain import run\n\n"
    for case in cases:
        text += f"\ndef test_{case.name}():\n    request = {case.request!r}\n    before = copy.deepcopy(request)\n"
        if case.error:
            text += f"    with pytest.raises({case.error}):\n        run(request)\n"
        else:
            text += f"    assert run(request) == {case.expected!r}\n"
        text += "    assert request == before\n"
    return text + "\n" + extra


def write_files(root, files):
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)


def changed(files, mutations):
    for mutation in mutations:
        files = mutation.apply(files)
    return files


def execute(work, report):
    plugin = Path(__file__).resolve().parents[1] / "grading"
    env = dict(
        os.environ,
        PYTHONPATH=os.pathsep.join([str(work), str(plugin)]),
        PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
        PYTHONDONTWRITEBYTECODE="1",
        PYTEST_ADDOPTS="",
        TSMC_REPORT_PATH=str(report),
    )
    completed = subprocess.run(
        [
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
        ],
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    report.with_suffix(".log").write_text(completed.stdout + completed.stderr)
    if not report.exists():
        raise ValueError(f"No test report: {report}; {completed.stdout[-1500:]}")
    result = json.loads(report.read_text())
    if completed.returncode not in {0, 1} or not result["collected"]:
        raise ValueError(f"Invalid collection: {report}; {completed.stdout[-1800:]}")
    return result


def build_task(task: Task, destination: Path):
    destination = destination.resolve()
    if destination.exists():
        raise ValueError(f"Authoring destination already exists: {destination}")
    destination.mkdir(parents=True)
    public = [case for case in task.cases if case.public]
    hidden = [case for case in task.cases if not case.public]
    if (
        len(public) < 3
        or len(hidden) < 5
        or len({c.name for c in task.cases}) != len(task.cases)
    ):
        raise ValueError(f"{task.task_id}: insufficient or duplicate cases")
    baseline = changed(task.files, task.faults)
    problem = f"# {task.task_id}: {task.title}\n\n" + (
        "A synthetic manufacturing service violates its documented contract. Diagnose "
        "the issue from the public examples and repair the implementation for all valid inputs.\n\n"
        "Run `python -m pytest -q tests` and read `docs/contract.md`. Public tests include "
        "known baseline failures. Submit a unified code diff against the original commit.\n\n"
        "Allowed changes: regular Python files under `fabops/` and new `tests/test_agent_*.py`. "
        "Preserve existing tests, data, documentation and configuration. No external dependencies, "
        "network access, background services, symlinks or grader hooks are allowed. "
        "The evaluator runs separately after submission; hidden feedback is not available during repair.\n\n"
        "This is a synthetic software issue, not a real company's production incident.\n"
    )
    fixture = next(case for case in public if not case.error)
    scaffold = {
        ".gitignore": "__pycache__/\n.pytest_cache/\n*.pyc\n",
        "fabops/__init__.py": '"""Synthetic manufacturing service."""\n',
        "fabops/__main__.py": CLI,
        "requirements-dev.txt": REQUIREMENTS,
        "problem_statement.md": problem,
        "README.md": f"# {task.title}\n\nRun `python -m fabops --input data/request.json`. "
        "See `docs/contract.md` and `tests/test_public.py`.\n",
        "docs/contract.md": f"# Public behavior contract\n\n{task.contract.strip()}\n\n"
        "The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. "
        "Do not mutate the request, including on rejected operations. "
        "Only the documented valid input domain is tested.\n",
        "tests/test_public.py": tests(
            public, task.extra_public_tests + "\n" + CLI_TEST
        ),
        "data/request.json": json.dumps(fixture.request, indent=2) + "\n",
        "data/expected.json": json.dumps(fixture.expected, indent=2) + "\n",
    }
    write_files(destination / "agent", {**scaffold, **baseline})
    author = destination / "author"
    write_files(
        author,
        {
            "tests/test_hidden.py": tests(hidden, task.extra_hidden_tests),
            "data/README.md": "Expected outputs are literal author-reviewed cases in the test suite.\n",
            "NOTES.md": f"# Author notes\n\nDesign difficulty: {task.difficulty}. "
            f"{task.difficulty_reason}\n\nFamily: `{task.family}`. References: "
            + ", ".join(task.references)
            + ".\n\nFixtures are newly authored. No external dataset rows are redistributed.\n",
        },
    )
    with tempfile.TemporaryDirectory(prefix="tsmc-author-") as temporary:
        work = Path(temporary) / "workspace"
        copy_tree(destination / "agent", work)
        commit = init_git(work)
        copy_tree(author / "tests", work / "assessment/tests")
        reports = {}
        reports["baseline"] = execute(work, destination / "baseline-report.json")
        write_files(work, task.files)
        git(work, "add", "fabops")
        gold_patch = git(work, "diff", "--cached", "--binary")
        if not gold_patch:
            raise ValueError(f"{task.task_id}: empty gold patch")
        (author / "gold.patch").write_text(gold_patch)
        for name, source in task.files.items():
            if source != baseline[name]:
                write_files(author / "reference_changes", {name: source})
        reports["gold"] = execute(work, destination / "gold-report.json")
        reports["gold_repeat"] = execute(work, destination / "gold-repeat-report.json")
        for name, mutations in task.mutants.items():
            mutant = changed(task.files, mutations)
            if mutant == baseline or mutant == task.files:
                raise ValueError(
                    f"{task.task_id}: mutant must differ from baseline and gold: {name}"
                )
            write_files(work, mutant)
            write_files(
                author / "mutants" / name,
                {key: value for key, value in mutant.items() if value != baseline[key]},
            )
            reports[name] = execute(work, destination / f"mutant-{name}-report.json")
    required = sorted(reports["gold"]["collected"])
    partitions = {"FAIL_TO_PASS": [], "PASS_TO_PASS": []}
    for name, report in reports.items():
        statuses = {key: value["status"] for key, value in report["tests"].items()}
        if sorted(report["collected"]) != required or set(statuses) != set(required):
            raise ValueError(f"{task.task_id}: unstable collection for {name}")
        if any(value not in {"passed", "failed"} for value in statuses.values()):
            raise ValueError(f"{task.task_id}: invalid outcome for {name}")
        if name.startswith("gold") != all(
            status == "passed" for status in statuses.values()
        ):
            raise ValueError(
                f"{task.task_id}: incorrect verdict for {name}; see {destination}"
            )
    for node in required:
        status = reports["baseline"]["tests"][node]["status"]
        partitions["PASS_TO_PASS" if status == "passed" else "FAIL_TO_PASS"].append(
            node
        )
    if min(map(len, partitions.values())) < 2:
        raise ValueError(
            f"{task.task_id}: need at least two regression and two failing cases"
        )
    write_json(
        author / "tests_manifest.json",
        {
            "task_id": task.task_id,
            **partitions,
            "required": required,
            "visibility": {
                node: "public" if node.startswith("tests/") else "hidden"
                for node in required
            },
        },
    )
    metadata = dict(
        task_id=task.task_id,
        title=task.title,
        version=task.version,
        language="en",
        track={"F": "factory_logic", "A": "data_analysis", "R": "reliability"}[
            task.task_id[0]
        ],
        split="dev" if task.task_id in DEV_TASKS else "test",
        family_id=task.family,
        difficulty="unmeasured",
        design_difficulty=task.difficulty,
        difficulty_evidence="author_review",
        difficulty_reason=task.difficulty_reason,
        source_kind="authored_synthetic",
        reference_sources=list(task.references),
        baseline_git_commit=commit,
        agent_file_sha256=file_hashes(destination / "agent"),
        test_count=len(required),
        public_tests=sum(n.startswith("tests/") for n in required),
        hidden_tests=sum(n.startswith("assessment/") for n in required),
        status="author_fixture_validated",
        reference_is_not_unique=True,
    )
    write_json(destination / "task.json", metadata)
    for path in destination.glob("*-report.*"):
        path.unlink()
    print(
        f"{task.task_id}: {task.difficulty}, {metadata['split']}, "
        f"{len(required)} tests, {len(partitions['FAIL_TO_PASS'])} FAIL_TO_PASS",
        flush=True,
    )
    return metadata


def main():
    from .catalog import tasks

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(".generated/tsmc-authored"))
    parser.add_argument("--task", action="append")
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    selected = [task for task in tasks() if not args.task or task.task_id in args.task]
    args.output.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(
            pool.map(
                lambda task: build_task(task, args.output / task.task_id), selected
            )
        )


if __name__ == "__main__":
    main()
