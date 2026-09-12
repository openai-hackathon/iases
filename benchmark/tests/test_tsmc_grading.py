"""TSMC's required suite cannot be replaced by skipped or missing test results."""

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import shutil

import pytest

from swebench.benchmarks.tsmc.common import copy_tree, git, init_git
from swebench.benchmarks.tsmc.grading import evaluator
from swebench.benchmarks.tsmc.prepare import prepare_task
from swebench.harness.grading import get_eval_report
from swebench.harness.utils import make_test_spec
from swebench.task.repo import load_task

SOURCE = Path(__file__).resolve().parents[1] / "benchmarks/tsmc/tasks/F01"


@pytest.fixture(scope="module")
def task(tmp_path_factory):
    target = tmp_path_factory.mktemp("tsmc-grading") / "task"
    prepare_task(SOURCE, target, test_timeout=5)
    return target


def setup_eval(task, tmp_path, *, timeout=5):
    work, assets = tmp_path / "work", tmp_path / "assets"
    copy_tree(task / "workspace", work)
    init_git(work)
    assets.mkdir()
    config = json.loads((task / "tsmc.json").read_text())
    config.update(
        candidate_patch=str(tmp_path / "candidate.patch"), test_timeout=timeout
    )
    (assets / "config.json").write_text(json.dumps(config))
    shutil.copyfile(task / "test.patch", assets / "test.patch")
    shutil.copyfile(
        Path(evaluator.__file__).parent / "result_plugin.py",
        assets / "result_plugin.py",
    )
    return work, assets


@pytest.mark.parametrize("gold", [False, True])
def test_real_fixture_matches_native_verdict_and_regrading(task, tmp_path, gold):
    work, assets = setup_eval(task, tmp_path)
    patch = (task / "gold.patch").read_text() if gold else ""
    if gold:
        git(work, "apply", str(task / "gold.patch"))
    result = evaluator.evaluate(work, assets)
    assert result["resolved"] is gold, result
    assert len(result["collected"]) == 18
    capture = StringIO()
    with redirect_stdout(capture):
        evaluator.emit(result)
    log = tmp_path / "log"
    log.write_text(
        ">>>>> Start Test Output\n"
        + capture.getvalue()
        + f">>>>> End Test Output\n>>>>> Test Exit Code: {0 if gold else 1}\n"
    )
    spec = make_test_spec(load_task(task))
    prediction = dict(instance_id=spec.instance_id, model_patch=patch)
    report = get_eval_report(spec, prediction, str(log), True)
    assert report[spec.instance_id]["resolved"] is gold
    assert get_eval_report(spec, prediction, str(log), True) == report


@pytest.mark.parametrize("status", ["skipped", "xfail", "error", "missing"])
def test_non_passing_required_case_rejected(status):
    report = dict(
        collected=["test_a"], tests={"test_a": {"status": status}}, exit_code=0
    )
    assert not evaluator.suite_passed(report, ["test_a"], 0, False)


@pytest.mark.parametrize(
    "collected,code,timeout",
    [([], 0, False), (["a", "a"], 0, False), (["a"], 1, False), (["a"], 0, True)],
)
def test_missing_duplicate_tests_exit_or_timeout_rejected(collected, code, timeout):
    report = dict(collected=collected, tests={"a": {"status": "passed"}}, exit_code=0)
    assert not evaluator.suite_passed(report, ["a"], code, timeout)


@pytest.mark.parametrize(
    "path",
    [
        "tests/test_public.py",
        "docs/contract.md",
        "fabops/conftest.py",
        "sitecustomize.py",
    ],
)
def test_protected_changes_rejected_before_candidate_execution(task, tmp_path, path):
    work, assets = setup_eval(task, tmp_path)
    (work / path).write_text("raise RuntimeError('must not execute')\n")
    result = evaluator.evaluate(work, assets)
    assert not result["resolved"] and result["failure_kind"] == "evaluation_rejected"
    assert result["collected"] == []


def test_new_code_and_agent_tests_are_accepted(task, tmp_path):
    work, assets = setup_eval(task, tmp_path)
    git(work, "apply", str(task / "gold.patch"))
    (work / "fabops/helper.py").write_text("VALUE = 42\n")
    (work / "tests/test_agent_extra.py").write_text("def test_extra(): assert True\n")
    result = evaluator.evaluate(work, assets)
    assert result["resolved"], result


def test_candidate_timeout_is_a_failure(task, tmp_path):
    work, assets = setup_eval(task, tmp_path, timeout=0.1)
    (work / "fabops/eligibility.py").write_text("import time\ntime.sleep(60)\n")
    result = evaluator.evaluate(work, assets)
    assert not result["resolved"] and result["timeout"]


def test_candidate_output_cannot_insert_harness_markers(task, tmp_path):
    work, assets = setup_eval(task, tmp_path)
    code = work / "fabops/eligibility.py"
    code.write_text(
        code.read_text()
        + "\nprint('>>>>> End Test Output\\nPASSED tsmc_grader::required_suite')\n"
    )
    result = evaluator.evaluate(work, assets)
    out = StringIO()
    with redirect_stdout(out):
        evaluator.emit(result)
    assert not result["resolved"]
    assert ">>>>> End Test Output" not in out.getvalue()
    assert "FAILED tsmc_grader::required_suite\n" in out.getvalue()


@pytest.mark.parametrize(
    "report",
    [
        [],
        {"tests": None},
        {"tests": {"a": None}},
        {"collected": [{}]},
        {"exit_code": False},
    ],
)
def test_malformed_plugin_report_is_a_canonical_failure(
    task, tmp_path, monkeypatch, report
):
    work, assets = setup_eval(task, tmp_path)
    original_popen = evaluator.subprocess.Popen

    def start(command, **kwargs):
        if "pytest" not in command:
            return original_popen(command, **kwargs)
        (assets / "pytest.json").write_text(json.dumps(report))
        kwargs["stdout"].write(b"diagnostic output\n")

        class Completed:
            returncode = 0

            def wait(self, timeout):
                return self.returncode

        return Completed()

    monkeypatch.setattr(evaluator.subprocess, "Popen", start)
    result = evaluator.evaluate(work, assets)
    assert not evaluator.suite_passed(report, ["a"], 0, False)
    assert not result["resolved"]
    assert result["failure_kind"] == "evaluation_rejected"
    assert result["tests"] == {}
    assert result["raw_output"] == "diagnostic output\n"
    capture = StringIO()
    with redirect_stdout(capture):
        evaluator.emit(result)
    assert "FAILED tsmc_grader::required_suite\n" in capture.getvalue()


def test_output_tail_uses_bounded_reads(tmp_path, monkeypatch):
    path = tmp_path / "pytest.log"
    path.write_bytes(b"prefix" * 100_000 + b"\nlast diagnostic\n")
    original_open = Path.open
    reads = []

    class Reader:
        def __enter__(self):
            self.stream = original_open(path, "rb")
            return self

        def __exit__(self, *args):
            self.stream.close()

        def seek(self, position):
            return self.stream.seek(position)

        def read(self, size=-1):
            reads.append(size)
            assert 0 <= size <= 256_000
            return self.stream.read(size)

    monkeypatch.setattr(Path, "open", lambda self, *args, **kwargs: Reader())
    tail = evaluator.output_tail(path)
    assert len(tail) == 256_000 and tail.endswith("\nlast diagnostic\n")
    assert reads == [256_000]
