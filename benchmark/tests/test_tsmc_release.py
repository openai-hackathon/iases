"""Release integrity, reserved-split isolation and content-sensitive exports."""

from collections import Counter
import json
from pathlib import Path
import shutil

from datasets import load_dataset
import pytest

from swebench.benchmarks.tsmc.authoring.catalog import tasks
from swebench.benchmarks.tsmc.common import file_hashes
from swebench.benchmarks.tsmc.prepare import prepare
from swebench.benchmarks.tsmc.release import (
    BASE_RELEASE_FILE,
    BASE_TASKS,
    HARD_DEVELOPMENT,
    HARD_EXTENSION,
    REVISED_DEVELOPMENT,
    REVISED_HARD,
    V2_FIXTURES,
    V2_RELEASE_FILE,
    V3_FIXTURES,
    V3_RELEASE_FILE,
    extend_release,
    revise_development_release,
    revise_hard_release,
    verify_release,
)
from swebench.task.repo import load_task_repo

SOURCE = Path(__file__).resolve().parents[1] / "benchmarks/tsmc"


def test_frozen_release_counts_families_and_later_difficulty_policy():
    release = verify_release(SOURCE)
    rows = release["tasks"]
    assert len(rows) == 90
    assert Counter(r["split"] for r in rows) == {"demo_dev": 12, "dev": 23, "test": 55}
    later = [r for r in rows if r["cohort"] == "later_20_70_10"]
    assert Counter(r["design_difficulty"] for r in later) == {
        "easy": 5,
        "medium": 17,
        "hard": 2,
    }
    assert all(r["measured_difficulty"] == "unmeasured" for r in rows)
    development = {r["family"] for r in rows if r["split"] != "test"}
    heldout = {r["family"] for r in rows if r["split"] == "test"}
    assert development.isdisjoint(heldout)
    assert len(tasks()) == 78
    previous = json.loads((SOURCE / BASE_RELEASE_FILE).read_text())
    assert sum(r["required_tests"] for r in previous["tasks"]) == 981
    extension = [r for r in rows if r["cohort"] == "hard_extension"]
    assert {r["task_id"] for r in extension} == HARD_EXTENSION
    assert all(r["design_difficulty"] == "hard" for r in extension)
    assert {r["task_id"] for r in extension if r["split"] == "dev"} == HARD_DEVELOPMENT


def test_extension_preserves_every_original_file_and_task_assignment():
    previous = json.loads((SOURCE / BASE_RELEASE_FILE).read_text())
    current = json.loads((SOURCE / V2_RELEASE_FILE).read_text())
    assert current["predecessor"]["content_sha256"] == previous["content_sha256"]
    assert all(
        current["files"][path] == expected
        for path, expected in previous["files"].items()
    )
    assert [r for r in current["tasks"] if r["task_id"] in BASE_TASKS] == previous[
        "tasks"
    ]


def test_hard_extension_validation_matches_the_frozen_fixtures():
    release = json.loads((SOURCE / V2_RELEASE_FILE).read_text())
    report = json.loads((SOURCE / "reports/native_hard_10_validation.json").read_text())
    assert report["release_sha256"] == release["content_sha256"]
    assert report["all_qualified"] is True
    assert {row["task_id"] for row in report["tasks"]} == HARD_EXTENSION
    for row in report["tasks"]:
        assert not row["issues"]
        assert row["variants"]["gold"]["resolved"]
        assert row["variants"]["gold_repeat"]["resolved"]
        assert all(count > 0 for count in row["mutant_hidden_failures"].values())
        assert len(row["mutant_hidden_failures"]) >= 4


def test_extension_cannot_silently_rewrite_its_predecessor(tmp_path):
    source = tmp_path / "source"
    shutil.copytree(SOURCE, source)
    path = source / BASE_RELEASE_FILE
    path.write_text(path.read_text() + "\n")
    with pytest.raises(ValueError, match="archive is missing or changed"):
        verify_release(source)


def test_release_migration_rejects_an_already_extended_release(tmp_path):
    source = tmp_path / "source"
    shutil.copytree(SOURCE, source)
    before = (source / "release.json").read_bytes()
    with pytest.raises(ValueError, match="Only the original"):
        extend_release(source)
    assert (source / "release.json").read_bytes() == before


def test_explicit_migration_checks_old_content_before_publishing_v2(tmp_path):
    source = tmp_path / "source"
    shutil.copytree(SOURCE, source)
    restore_v2_tasks(source)
    archive = (source / BASE_RELEASE_FILE).read_bytes()
    (source / "release.json").write_bytes(archive)
    extended = extend_release(source)
    assert extended == verify_release(source)
    assert extended["release"] == "manufacturing-90-v2"
    assert (source / BASE_RELEASE_FILE).read_bytes() == archive


def test_frozen_source_drift_is_rejected(tmp_path):
    source = tmp_path / "source"
    shutil.copytree(SOURCE, source)
    path = source / "tasks/F06/author/tests/test_hidden.py"
    path.write_text(path.read_text() + "\n# Accidental change after freeze.\n")
    with pytest.raises(ValueError, match="must not modify .*frozen fixtures"):
        verify_release(source)


def restore_v2_tasks(source):
    restore_v3_tasks(source)
    for key in REVISED_DEVELOPMENT:
        shutil.rmtree(source / "tasks" / key)
        shutil.copytree(source / V2_FIXTURES / "tasks" / key, source / "tasks" / key)


def restore_v3_tasks(source):
    for key in REVISED_HARD:
        shutil.rmtree(source / "tasks" / key)
        shutil.copytree(source / V3_FIXTURES / "tasks" / key, source / "tasks" / key)


def test_revision_preserves_all_other_tasks_and_original_selected_fixtures():
    previous = json.loads((SOURCE / V2_RELEASE_FILE).read_text())
    current = json.loads((SOURCE / V3_RELEASE_FILE).read_text())
    assert current["release"] == "manufacturing-90-v3"
    assert current["predecessor"]["content_sha256"] == previous["content_sha256"]
    old_rows = {row["task_id"]: row for row in previous["tasks"]}
    for row in current["tasks"]:
        if row["task_id"] not in REVISED_DEVELOPMENT:
            assert row == old_rows[row["task_id"]]
        else:
            assert row["instance_id"].endswith("-v2.0")
            assert row["split"] == "dev"
            assert row["required_tests"] > old_rows[row["task_id"]]["required_tests"]
    for path, expected in previous["files"].items():
        revised = path.startswith(tuple(f"tasks/{key}/" for key in REVISED_DEVELOPMENT))
        current_path = f"{V2_FIXTURES}/{path}" if revised else path
        assert current["files"][current_path] == expected


def test_native_development_validation_matches_v3_instances():
    release = json.loads((SOURCE / V3_RELEASE_FILE).read_text())
    report = json.loads(
        (SOURCE / "reports/native_development_revision_validation.json").read_text()
    )
    assert report["release_sha256"] == release["content_sha256"]
    assert report["all_qualified"] is True
    assert {row["task_id"] for row in report["tasks"]} == REVISED_DEVELOPMENT
    metadata = {row["task_id"]: row for row in release["tasks"]}
    for row in report["tasks"]:
        assert row["instance_id"] == metadata[row["task_id"]]["instance_id"]
        assert row["original_test_count"] == metadata[row["task_id"]]["required_tests"]
        assert not row["issues"]
        assert not row["variants"]["baseline"]["resolved"]
        assert row["variants"]["gold"]["resolved"]
        assert row["variants"]["gold_repeat"]["resolved"]
        assert len(row["mutant_hidden_failures"]) >= 6
        assert all(count > 0 for count in row["mutant_hidden_failures"].values())


def test_explicit_development_migration_and_repeated_migration(tmp_path):
    source = tmp_path / "source"
    shutil.copytree(SOURCE, source)
    restore_v3_tasks(source)
    (source / "release.json").write_bytes((source / V2_RELEASE_FILE).read_bytes())
    revised = revise_development_release(source)
    assert revised == verify_release(source)
    before = (source / "release.json").read_bytes()
    with pytest.raises(ValueError, match="Only the original manufacturing-90-v2"):
        revise_development_release(source)
    assert (source / "release.json").read_bytes() == before


@pytest.mark.parametrize(
    "kind", ["old_fixture", "unrelated_file", "partial_revision", "difficulty", "split"]
)
def test_revision_rejects_changes_outside_its_contract(tmp_path, kind):
    source = tmp_path / "source"
    shutil.copytree(SOURCE, source)
    restore_v3_tasks(source)
    (source / "release.json").write_bytes((source / V2_RELEASE_FILE).read_bytes())
    if kind == "old_fixture":
        path = source / V2_FIXTURES / "tasks/A12/agent/fabops/domain.py"
        path.write_text(path.read_text() + "\n# Drift in archived implementation.\n")
    elif kind == "unrelated_file":
        (source / "tasks/F05/agent/new_file.txt").write_text("Unrelated addition.\n")
    else:
        path = source / "tasks/A12/task.json"
        task = json.loads(path.read_text())
        task[
            {
                "partial_revision": "version",
                "difficulty": "design_difficulty",
                "split": "split",
            }[kind]
        ] = {"partial_revision": "1.0", "difficulty": "hard", "split": "test"}[kind]
        path.write_text(json.dumps(task))
    before = (source / "release.json").read_bytes()
    with pytest.raises(ValueError):
        revise_development_release(source)
    assert (source / "release.json").read_bytes() == before


def test_hard_revision_preserves_all_unselected_tasks_and_v3_originals():
    previous = json.loads((SOURCE / V3_RELEASE_FILE).read_text())
    current = verify_release(SOURCE)
    assert current["release"] == "manufacturing-90-v4"
    assert current["predecessor"]["content_sha256"] == previous["content_sha256"]
    old_rows = {row["task_id"]: row for row in previous["tasks"]}
    assert REVISED_HARD == {
        row["task_id"]
        for row in previous["tasks"]
        if row["design_difficulty"] == "hard"
        and row["task_id"] not in {"A29", "F25", "R29"}
    }
    for row in current["tasks"]:
        old = old_rows[row["task_id"]]
        if row["task_id"] not in REVISED_HARD:
            assert row == old
        else:
            assert row["instance_id"].endswith("-v2.0")
            assert row["split"] == old["split"]
            assert row["required_tests"] > old["required_tests"]
    for path, expected in previous["files"].items():
        revised = path.startswith(tuple(f"tasks/{key}/" for key in REVISED_HARD))
        current_path = f"{V3_FIXTURES}/{path}" if revised else path
        assert current["files"][current_path] == expected


def test_explicit_hard_migration_and_repeated_migration(tmp_path):
    source = tmp_path / "source"
    shutil.copytree(SOURCE, source)
    (source / "release.json").write_bytes((source / V3_RELEASE_FILE).read_bytes())
    revised = revise_hard_release(source)
    assert revised == verify_release(source)
    before = (source / "release.json").read_bytes()
    with pytest.raises(ValueError, match="Only the original manufacturing-90-v3"):
        revise_hard_release(source)
    assert (source / "release.json").read_bytes() == before


def test_native_hard_revision_validation_matches_current_instances():
    release = verify_release(SOURCE)
    report = json.loads(
        (SOURCE / "reports/native_hard_revision_9_validation.json").read_text()
    )
    assert report["release_sha256"] == release["content_sha256"]
    assert report["all_qualified"] is True
    assert report["docker_executions"] == 115
    assert {row["task_id"] for row in report["tasks"]} == REVISED_HARD
    metadata = {row["task_id"]: row for row in release["tasks"]}
    for row in report["tasks"]:
        assert row["instance_id"] == metadata[row["task_id"]]["instance_id"]
        assert row["original_test_count"] == metadata[row["task_id"]]["required_tests"]
        assert not row["issues"]
        assert not row["variants"]["baseline"]["resolved"]
        assert row["variants"]["gold"]["resolved"]
        assert row["variants"]["gold_repeat"]["resolved"]
        assert len(row["mutant_hidden_failures"]) >= 8
        assert all(count > 0 for count in row["mutant_hidden_failures"].values())


@pytest.mark.parametrize(
    "kind",
    [
        "old_fixture",
        "old_manifest",
        "unrelated_file",
        "partial_revision",
        "difficulty",
        "split",
        "A29",
        "F25",
        "R29",
    ],
)
def test_hard_revision_rejects_changes_outside_its_contract(tmp_path, kind):
    source = tmp_path / "source"
    shutil.copytree(SOURCE, source)
    (source / "release.json").write_bytes((source / V3_RELEASE_FILE).read_bytes())
    if kind == "old_fixture":
        path = source / V3_FIXTURES / "tasks/F19/agent/fabops/domain.py"
        path.write_text(path.read_text() + "\n# Archive drift.\n")
    elif kind == "old_manifest":
        path = source / V3_RELEASE_FILE
        path.write_text(path.read_text() + "\n")
    elif kind == "unrelated_file":
        (source / "tasks/F05/agent/new_file.txt").write_text("Unrelated addition.\n")
    elif kind in {"A29", "F25", "R29"}:
        path = source / "tasks" / kind / "author/tests/test_hidden.py"
        path.write_text(path.read_text() + "\n# Protected task drift.\n")
    else:
        path = source / "tasks/F19/task.json"
        task = json.loads(path.read_text())
        task[
            {
                "partial_revision": "version",
                "difficulty": "design_difficulty",
                "split": "split",
            }[kind]
        ] = {"partial_revision": "1.0", "difficulty": "medium", "split": "test"}[kind]
        path.write_text(json.dumps(task))
    before = (source / "release.json").read_bytes()
    with pytest.raises(ValueError):
        revise_hard_release(source)
    assert (source / "release.json").read_bytes() == before


@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    root = tmp_path_factory.mktemp("tsmc-release-exports")
    prepare(SOURCE, root / "default", ["F01", "F05", "F06"])
    prepare(SOURCE, root / "explicit", ["F01", "F05", "F06"], export_test=True)
    return root


def test_public_export_omits_reserved_tasks_until_explicitly_requested(exported):
    default = exported / "default"
    assert not (default / "heldout-public").exists()
    assert {p.name for p in (default / "public").glob("*.parquet")} == {
        "demo_dev.parquet",
        "dev.parquet",
    }
    loaded = load_dataset(str(default / "public"))
    assert set(loaded) == {"demo_dev", "dev"}
    assert loaded["dev"][0]["task_id"] == "F05"
    assert all(
        not any(
            k in row for k in ("patch", "test_patch", "FAIL_TO_PASS", "eval_script")
        )
        for split in loaded.values()
        for row in split
    )
    heldout = load_dataset(str(exported / "explicit/heldout-public"), split="test")
    assert [row["task_id"] for row in heldout] == ["F06"]
    assert file_hashes(default / "public") == file_hashes(exported / "explicit/public")
    assert {i["split"] for i in load_task_repo(default / "task-repo")} == {
        "demo_dev",
        "dev",
        "test",
    }


def test_different_contents_in_same_named_export_do_not_reuse_stale_cache(
    exported, tmp_path
):
    other = tmp_path / "other"
    prepare(SOURCE, other, ["F01", "F05", "A05"])
    first = load_dataset(str(exported / "default/public"), split="dev")
    second = load_dataset(str(other / "public"), split="dev")
    assert len(first) == 1
    assert {r["task_id"] for r in second} == {"F05", "A05"}


def test_authored_cases_have_literal_unique_inputs_and_multiple_wrong_repairs():
    for task in tasks():
        assert len(task.mutants) >= 2
        requests = [json.dumps(case.request, sort_keys=True) for case in task.cases]
        assert len(requests) == len(set(requests)), task.task_id
        if task.difficulty == "hard":
            assert len({change.path for change in task.faults}) >= 2
        if task.task_id in HARD_EXTENSION:
            assert len(task.faults) >= 3
            assert len(task.mutants) >= 4
            assert sum(case.public for case in task.cases) >= 4
            assert sum(not case.public for case in task.cases) >= 10
        agent = SOURCE / "tasks" / task.task_id / "agent"
        metadata = json.loads((agent.parent / "task.json").read_text())
        assert metadata["version"] == task.version
        assert file_hashes(agent) == metadata["agent_file_sha256"]
