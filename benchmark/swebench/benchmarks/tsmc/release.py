"""Freeze author fixtures and audit the reserved evaluation partition."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path

from swebench.benchmarks.tsmc.common import file_hashes, instance_id

RELEASE_FILE = "release.json"
BASE_RELEASE_FILE = "releases/manufacturing-80-v1.json"
BASE_RELEASE_SHA256 = "91cb193efc227e46ae53d6d38315daeaf4e0b9cfe0ca54ff19fb4fdbe38e8f05"
V2_RELEASE_FILE = "releases/manufacturing-90-v2.json"
V2_RELEASE_SHA256 = "14c3e4bad4249d3bb5baab06eeaf7f8930ad5c6a1354355c1ffc3b4f1d0a97de"
V2_FIXTURES = "releases/manufacturing-90-v2"
REVISED_DEVELOPMENT = {"A12", "F11", "R13", "R21", "A29", "F25", "R29"}
V3_RELEASE_FILE = "releases/manufacturing-90-v3.json"
V3_RELEASE_SHA256 = "2d8803f6daf12d088105e28a15659c841b6c84605c2cce14de4877efaafda54e"
V3_FIXTURES = "releases/manufacturing-90-v3"
REVISED_HARD = {"A30", "A31", "F19", "F26", "F27", "R22", "R30", "R31", "R32"}
BASE_TASKS = {
    *[f"F{i:02d}" for i in range(1, 25)],
    *[f"A{i:02d}" for i in range(1, 29)],
    *[f"R{i:02d}" for i in range(1, 29)],
}
HARD_EXTENSION = {"R29", "R30", "R31", "R32", "F25", "F26", "F27", "A29", "A30", "A31"}
HARD_DEVELOPMENT = {"R29", "F25", "A29"}
RELATED_FAMILIES = {
    "F05": "expiry_boundary",
    "R07": "expiry_boundary",
    "F04": "unit_conversion_scaling",
    "A22": "unit_conversion_scaling",
    "A01": "interval_union",
    "F11": "interval_union",
    "A02": "record_identity_aggregation",
    "A19": "record_identity_aggregation",
}
LATER_COHORT = {
    "F19",
    "F20",
    "F21",
    "F22",
    "F23",
    "F24",
    *[f"A{i}" for i in range(20, 29)],
    *[f"R{i}" for i in range(20, 29)],
}


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def snapshot(source: Path):
    hashes = {
        f"tasks/{name}": value for name, value in file_hashes(source / "tasks").items()
    }
    hashes.update(
        {
            f"scenarios/{name}": value
            for name, value in file_hashes(source / "scenarios").items()
        }
    )
    hashes["sources.json"] = hashlib.sha256(
        (source / "sources.json").read_bytes()
    ).hexdigest()
    return hashes


def archived_release(source, name, expected_hash):
    path = source / name
    if (
        not path.is_file()
        or hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash
    ):
        raise ValueError(f"The release archive is missing or changed: {name}")
    return json.loads(path.read_text())


def check_revision(source, files, rows):
    """Require exactly seven versioned dev replacements and retain their originals."""
    previous = archived_release(source, V2_RELEASE_FILE, V2_RELEASE_SHA256)
    old_rows = {row["task_id"]: row for row in previous["tasks"]}
    for row in rows:
        key = row["task_id"]
        old = old_rows[key]
        if key not in REVISED_DEVELOPMENT:
            if row != old:
                raise ValueError(f"The development revision must preserve task {key}")
            continue
        if (
            row["instance_id"] != instance_id(key, "2.0")
            or row["split"] != "dev"
            or row["design_difficulty"] != old["design_difficulty"]
            or row["cohort"] != old["cohort"]
        ):
            raise ValueError(
                "All seven revised tasks must keep their difficulty and dev split at version 2.0"
            )
    archived = file_hashes(source / V2_FIXTURES)
    expected_archived = {}
    for path, expected in previous["files"].items():
        parts = Path(path).parts
        if len(parts) > 1 and parts[0] == "tasks" and parts[1] in REVISED_DEVELOPMENT:
            expected_archived[path] = expected
        elif files.get(path) != expected:
            raise ValueError(
                f"The development revision must not modify unchanged frozen fixtures: {path}"
            )
    if archived != expected_archived:
        raise ValueError("Archived v2 task fixtures are missing or changed")
    unchanged = {
        key: value
        for key, value in files.items()
        if not any(key.startswith(f"tasks/{task}/") for task in REVISED_DEVELOPMENT)
    }
    if set(unchanged) != set(previous["files"]) - set(expected_archived):
        raise ValueError("The development revision must not add unrelated frozen files")
    files[V2_RELEASE_FILE] = V2_RELEASE_SHA256
    files.update({f"{V2_FIXTURES}/{path}": value for path, value in archived.items()})
    return previous


def check_hard_revision(source, files, rows):
    """Verify the full v1→v3 chain and exactly nine explicitly scoped replacements."""
    previous = archived_release(source, V3_RELEASE_FILE, V3_RELEASE_SHA256)
    old_rows = {row["task_id"]: row for row in previous["tasks"]}
    for row in rows:
        key = row["task_id"]
        old = old_rows[key]
        if key not in REVISED_HARD:
            if row != old:
                raise ValueError(f"The hard revision must preserve task {key}")
        elif (
            row["instance_id"] != instance_id(key, "2.0")
            or row["split"] != old["split"]
            or row["design_difficulty"] != old["design_difficulty"]
            or row["cohort"] != old["cohort"]
        ):
            raise ValueError(
                "All nine hard revisions must keep their difficulty and split at version 2.0"
            )

    prefixes = tuple(f"tasks/{key}/" for key in REVISED_HARD)
    originals = {
        path: value
        for path, value in previous["files"].items()
        if path.startswith(prefixes)
    }
    archived = file_hashes(source / V3_FIXTURES)
    if archived != originals:
        raise ValueError("Archived v3 task fixtures are missing or changed")

    # Reconstruct v3's content view and validate its predecessor too. This keeps
    # original freeze guarantees active instead of trusting only the newest archive.
    historical = {
        path: value for path, value in files.items() if not path.startswith(prefixes)
    }
    historical.update(originals)
    historical_rows = [
        old_rows[row["task_id"]] if row["task_id"] in REVISED_HARD else row
        for row in rows
    ]
    check_revision(source, historical, historical_rows)
    if historical != previous["files"]:
        raise ValueError("The hard revision must not modify unrelated frozen fixtures")
    files.update(
        {
            path: value
            for path, value in historical.items()
            if path.startswith("releases/")
        }
    )
    files[V3_RELEASE_FILE] = V3_RELEASE_SHA256
    files.update({f"{V3_FIXTURES}/{path}": value for path, value in archived.items()})
    return previous


def release_content(source: Path):
    sources = json.loads((source / "sources.json").read_text())["sources"]
    rows = []
    for path in sorted((source / "tasks").glob("*/task.json")):
        task = json.loads(path.read_text())
        key = task["task_id"]
        if set(task.get("reference_sources", [])) - sources.keys():
            raise ValueError(f"Unknown source reference in {key}")
        manifest = json.loads((path.parent / "author/tests_manifest.json").read_text())
        row = dict(
            task_id=key,
            instance_id=instance_id(key, task["version"]),
            split=task["split"],
            design_difficulty=task.get("design_difficulty", "unrated"),
            measured_difficulty="unmeasured",
            family=(
                task["family_id"]
                if task["version"] == "2.0" and key in REVISED_DEVELOPMENT
                else RELATED_FAMILIES.get(key, task.get("family_id", f"legacy_{key}"))
            ),
            cohort=(
                "hard_extension"
                if key in HARD_EXTENSION
                else "later_20_70_10"
                if key in LATER_COHORT
                else "earlier"
            ),
            required_tests=len(manifest["required"]),
            fail_to_pass=len(manifest["FAIL_TO_PASS"]),
            pass_to_pass=len(manifest["PASS_TO_PASS"]),
        )
        rows.append(row)
    keys = {r["task_id"] for r in rows}
    extended = keys == BASE_TASKS | HARD_EXTENSION
    revised = any(
        row["instance_id"] == instance_id(row["task_id"], "2.0") for row in rows
    )
    hard_revised = any(
        row["task_id"] in REVISED_HARD
        and row["instance_id"] == instance_id(row["task_id"], "2.0")
        for row in rows
    )
    if revised and not extended:
        raise ValueError("Development revisions require the complete 90-task release")
    if keys != BASE_TASKS and not extended:
        raise ValueError(
            "Expected the frozen 80 tasks or all 90 tasks with the hard extension"
        )
    if len({r["instance_id"] for r in rows}) != len(rows):
        raise ValueError("The release must contain unique instances")
    expected_splits = (
        {"demo_dev": 12, "dev": 23, "test": 55}
        if extended
        else {"demo_dev": 12, "dev": 20, "test": 48}
    )
    if Counter(r["split"] for r in rows) != expected_splits:
        raise ValueError(f"Expected split counts: {expected_splits}")
    for row in rows:
        if row["task_id"] in HARD_EXTENSION:
            split = "dev" if row["task_id"] in HARD_DEVELOPMENT else "test"
            if row["design_difficulty"] != "hard" or row["split"] != split:
                raise ValueError(
                    "The ten-task hard extension must preserve its difficulty and split assignments"
                )
    later = Counter(
        r["design_difficulty"] for r in rows if r["cohort"] == "later_20_70_10"
    )
    if later != {"easy": 5, "medium": 17, "hard": 2}:
        raise ValueError(
            "The later 24-task cohort must follow the rounded 20/70/10 policy"
        )
    families = {}
    for row in rows:
        families.setdefault(row["family"], set()).add(
            "heldout" if row["split"] == "test" else "development"
        )
    if any(len(partitions) > 1 for partitions in families.values()):
        raise ValueError(
            "A related issue family crosses the development/heldout boundary"
        )
    files = snapshot(source)
    predecessor = None
    if extended:
        previous = archived_release(source, BASE_RELEASE_FILE, BASE_RELEASE_SHA256)
        files[BASE_RELEASE_FILE] = BASE_RELEASE_SHA256
        if hard_revised:
            previous = check_hard_revision(source, files, rows)
        elif revised:
            previous = check_revision(source, files, rows)
        elif any(
            files.get(path) != expected for path, expected in previous["files"].items()
        ):
            raise ValueError(
                "The hard extension must not modify original frozen fixtures"
            )
        if (
            not revised
            and [row for row in rows if row["task_id"] in BASE_TASKS]
            != previous["tasks"]
        ):
            raise ValueError(
                "The hard extension must preserve original task metadata and splits"
            )
        predecessor = dict(
            release=previous["release"],
            content_sha256=previous["content_sha256"],
            manifest=V3_RELEASE_FILE
            if hard_revised
            else V2_RELEASE_FILE
            if revised
            else BASE_RELEASE_FILE,
        )
    result = dict(
        schema_version=1,
        release="manufacturing-90-v4"
        if hard_revised
        else "manufacturing-90-v3"
        if revised
        else "manufacturing-90-v2"
        if extended
        else "manufacturing-80-v1",
        frozen_on="2026-09-12",
        scope="Authored synthetic manufacturing software repairs in an imagined semiconductor factory",
        split_policy="Reserved tasks are not used for model-driven prompt, agent or task tuning",
        confidentiality="Trusted author checkout includes private material; publish solver exports only",
        difficulty_policy=dict(
            target={"easy": 0.2, "medium": 0.7, "hard": 0.1},
            applies_to="later_20_70_10",
            actual=dict(later),
            method="Largest remainder allocation for 24 tasks",
        ),
        tasks=rows,
        files=files,
        content_sha256=digest(files),
    )
    if predecessor:
        result["predecessor"] = predecessor
        result["hard_extension_policy"] = dict(
            tasks=sorted(HARD_EXTENSION),
            design_difficulty="hard",
            measured_difficulty="unmeasured",
            development_tasks=sorted(HARD_DEVELOPMENT),
            rationale="Explicit request for ten additional hard tasks; the earlier 20/70/10 cohort remains unchanged",
        )
    if revised:
        result["development_revision_policy"] = dict(
            tasks=sorted(REVISED_DEVELOPMENT),
            version="2.0",
            previous_fixture_root=V2_FIXTURES,
            unchanged_tasks=83,
            unchanged_heldout_tasks=55,
            rationale="Reconstruct seven selected medium and hard development repairs after ceiling effects in the v2 pilot; preserve all easy and reserved tasks",
            calibration="Development-only calibration; author difficulty labels remain unmeasured until supported by repeated model trials",
        )
    if hard_revised:
        result["hard_revision_policy"] = dict(
            tasks=sorted(REVISED_HARD),
            version="2.0",
            previous_fixture_root=V3_FIXTURES,
            excluded_hard_tasks=sorted(HARD_DEVELOPMENT),
            unchanged_tasks=81,
            unchanged_heldout_tasks=47,
            rationale="Explicit request to substantially strengthen every hard task except A29, F25 and R29 while retaining scenario directions and split assignments",
            calibration="Author contract and mutation validation only; no model-driven heldout tuning or measured difficulty claim",
        )
        result["development_revision_policy"]["scope"] = (
            "Historical v2-to-v3 transition"
        )
    return result


def extend_release(source: Path):
    """Publish v2 only after verifying the archived v1 and every unchanged fixture."""
    path = source / RELEASE_FILE
    if (
        not path.is_file()
        or hashlib.sha256(path.read_bytes()).hexdigest() != BASE_RELEASE_SHA256
    ):
        raise ValueError(
            "Only the original manufacturing-80-v1 release can be extended"
        )
    content = release_content(source)
    if content["release"] != "manufacturing-90-v2":
        raise ValueError(
            "All ten hard tasks must be present before extending the release"
        )
    from swebench.inference.workspace_agent import atomic_write_json

    atomic_write_json(path, content)
    return content


def revise_development_release(source: Path):
    """Publish v3 once, with v2 originals and every unrelated fixture verified."""
    path = source / RELEASE_FILE
    if (
        not path.is_file()
        or hashlib.sha256(path.read_bytes()).hexdigest() != V2_RELEASE_SHA256
    ):
        raise ValueError("Only the original manufacturing-90-v2 release can be revised")
    content = release_content(source)
    if content["release"] != "manufacturing-90-v3":
        raise ValueError(
            "All seven development revisions must be present before publishing v3"
        )
    from swebench.inference.workspace_agent import atomic_write_json

    atomic_write_json(path, content)
    return content


def revise_hard_release(source: Path):
    """Publish v4 once, preserving v3 originals and every unselected task."""
    path = source / RELEASE_FILE
    if (
        not path.is_file()
        or hashlib.sha256(path.read_bytes()).hexdigest() != V3_RELEASE_SHA256
    ):
        raise ValueError("Only the original manufacturing-90-v3 release can be revised")
    content = release_content(source)
    if content["release"] != "manufacturing-90-v4":
        raise ValueError("All nine hard revisions must be present before publishing v4")
    from swebench.inference.workspace_agent import atomic_write_json

    atomic_write_json(path, content)
    return content


def freeze_release(source: Path):
    path = source / RELEASE_FILE
    if path.exists():
        raise ValueError(
            "A release is already frozen; create an explicit new release version"
        )
    content = release_content(source)
    path.write_text(json.dumps(content, indent=2, sort_keys=True) + "\n")
    return content


def verify_release(source: Path):
    path = source / RELEASE_FILE
    if not path.exists():
        return None
    recorded = json.loads(path.read_text())
    actual = release_content(source)
    if recorded != actual:
        raise ValueError(
            "Frozen release differs from its fixtures or split assignments"
        )
    return recorded
