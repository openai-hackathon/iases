"""The converted dataset must be reproducible and separate public/private material."""

import json
from pathlib import Path

from datasets import load_dataset
import pytest

from swebench.benchmarks.tsmc.common import file_hashes
from swebench.benchmarks.tsmc.prepare import prepare
from swebench.benchmarks.tsmc import GATE_TEST
from swebench.harness.utils import make_test_spec
from swebench.task.checks import check_task_repo
from swebench.task.publish import write_parquets
from swebench.task.repo import load_task_repo

SOURCE = Path(__file__).resolve().parents[1] / "benchmarks/tsmc"


def test_english_fixtures_match_provenance_and_preserve_executable_content():
    provenance = json.loads((SOURCE / "provenance.json").read_text())
    expected = provenance["files"]
    actual = file_hashes(SOURCE)
    assert len(expected) == 375
    assert {name: actual[name] for name in expected} == expected
    for name, sha in provenance["archive_files"].items():
        if not (
            name.endswith(".md")
            or name.endswith("/task.json")
            or name.startswith("scenarios/")
        ):
            assert actual[name] == sha


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    root = tmp_path_factory.mktemp("tsmc-native") / "generated"
    prepare(SOURCE, root, ["F01"])
    return root


def test_native_task_round_trip_and_public_loader(generated, tmp_path):
    repo = generated / "task-repo"
    assert check_task_repo(repo) == []
    (instance,) = load_task_repo(repo)
    assert instance["instance_id"] == "tsmc__f01-v0.2"
    assert GATE_TEST in instance["FAIL_TO_PASS"]
    assert make_test_spec(instance).container_profile == "python_offline"
    assert "assessment/tests/test_hidden.py" in instance["test_patch"]
    paths = write_parquets(repo, tmp_path / "evaluation")
    assert paths["local/TSMC-bench/demo_dev"].is_file()
    public = load_dataset(
        str(generated / "public"), split="demo_dev", cache_dir=str(tmp_path / "cache")
    )
    assert len(public) == 1 and public[0]["image_name"] == instance["image"]
    assert set(public.column_names) == {
        "instance_id",
        "repo",
        "version",
        "base_commit",
        "task_id",
        "image_name",
        "problem_statement",
    }
    assert file_hashes(
        repo / "tasks" / instance["instance_id"] / "workspace"
    ) == file_hashes(SOURCE / "tasks/F01/agent")


def test_preparation_is_reproducible_and_replaces_only_its_outputs(generated, tmp_path):
    second = tmp_path / "generated"
    prepare(SOURCE, second, ["F01"])
    assert file_hashes(generated) == file_hashes(second)
    before = file_hashes(second)
    prepare(SOURCE, second, ["F01"])
    assert file_hashes(second) == before
    unrelated = tmp_path / "user-data"
    unrelated.mkdir()
    (unrelated / "keep.txt").write_text("user data")
    with pytest.raises(ValueError, match="Refusing to replace"):
        prepare(SOURCE, unrelated, ["F01"])
    assert (unrelated / "keep.txt").read_text() == "user data"


def test_bad_selection_and_overlapping_output_fail_before_mutation(tmp_path):
    with pytest.raises(ValueError, match="Unknown"):
        prepare(SOURCE, tmp_path / "out", ["F99"])
    with pytest.raises(ValueError, match="overlap"):
        prepare(SOURCE, SOURCE / "generated", ["F01"])


def test_source_hash_drift_is_rejected(tmp_path):
    import shutil

    source = tmp_path / "source"
    shutil.copytree(SOURCE / "tasks/F01", source / "tasks/F01")
    (source / "tasks/F01/agent/fabops/eligibility.py").write_text("changed")
    with pytest.raises(ValueError, match="source hashes"):
        prepare(source, tmp_path / "out", ["F01"])
