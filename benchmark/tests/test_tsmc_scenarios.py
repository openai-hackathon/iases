"""Recovery semantics and actual bundled CLI compositions (no candidate on host)."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from swebench.benchmarks.tsmc.common import copy_tree
from swebench.benchmarks.tsmc.jsonio import decode_json
from swebench.benchmarks.tsmc.scenario.engine import replay
from swebench.benchmarks.tsmc.scenario.events import EventLog, read_events
from swebench.benchmarks.tsmc.scenario.probes import probe
from swebench.benchmarks.tsmc.scenario.reporting import summarize
from swebench.benchmarks.tsmc.scenario.runner import predictions_from

SOURCE = Path(__file__).resolve().parents[1] / "benchmarks" / "tsmc"


@pytest.mark.parametrize("number", ["NaN", "Infinity", "-Infinity", "1e999", "-1e999"])
def test_nonfinite_json_rejected_even_in_nested_fields(number):
    with pytest.raises(ValueError, match="Non-finite"):
        decode_json('{"trace": [{"value": ' + number + "}]}")


def spec(scenario="DC01"):
    return json.loads(
        (SOURCE / "scenarios" / "author" / scenario / "scenario.json").read_text()
    )


def grades(scenario, at=0, failed=()):
    return [
        dict(
            service=sid,
            task_id=cfg["task_id"],
            patch_sha256=hashlib.sha256(sid.encode()).hexdigest(),
            resolved=sid not in failed,
            at_seconds=at,
        )
        for sid, cfg in scenario["services"].items()
    ]


def successful_probe(sid, evidence, upstream):
    return dict(passed=True, artifact={})


@pytest.fixture(scope="module")
def fixture_cli(tmp_path_factory):
    """Only the trusted bundled gold/baseline may run on the development host."""
    root = tmp_path_factory.mktemp("trusted-composition")

    def invoke(task, payload, variant="gold"):
        directory = root / f"{task}-{variant}"
        if not directory.exists():
            copy_tree(SOURCE / "tasks" / task / "agent", directory)
            if variant == "gold":
                subprocess.run(
                    [
                        "git",
                        "apply",
                        str(SOURCE / "tasks" / task / "author" / "gold.patch"),
                    ],
                    cwd=directory,
                    check=True,
                    capture_output=True,
                )
        request = root / "request.json"
        request.write_text(json.dumps(payload))
        env = dict(PATH=os.environ["PATH"], PYTHONDONTWRITEBYTECODE="1")
        output = subprocess.run(
            [sys.executable, "-m", "fabops", "--input", str(request)],
            cwd=directory,
            env=env,
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )
        return json.loads(output.stdout)

    return invoke


@pytest.mark.parametrize("scenario", ["DC01", "DC02", "DC03", "DC04"])
def test_all_services_compose_actual_reference_outputs(scenario, fixture_cli, tmp_path):
    scenario_spec = spec(scenario)

    def compose(sid, evidence, upstream):
        task = scenario_spec["services"][sid]["task_id"]
        return probe(
            sid, task, upstream, lambda service, payload: fixture_cli(task, payload)
        )

    path = tmp_path / "events.jsonl"
    events = replay(
        scenario_spec,
        grades(scenario_spec),
        compose,
        log=EventLog("test", scenario, path),
    )
    report = summarize(events)
    assert report["restored_rate"] == 1, [
        (e["payload"].get("service"), e["payload"].get("result"))
        for e in events
        if e["kind"] == "probed"
    ]
    assert report["verified_rate"] == 1
    assert sum(e["kind"] == "probed" for e in events) == len(scenario_spec["services"])
    assert summarize(read_events(path)) == report
    assert report["first_all_protected_restored_seconds"] == (
        60 if scenario == "DC04" else 0
    )
    assert "author_environment_events" not in events[0]["payload"]["scenario"]


@pytest.mark.parametrize(
    "failed",
    [
        "journal",
        "state",
        "qualification",
        "release",
        "maintenance",
        "telemetry",
        "downtime",
    ],
)
def test_composition_detects_baseline_even_if_grade_claimed_pass(failed, fixture_cli):
    scenario_spec = spec()

    def compose(sid, evidence, upstream):
        task = scenario_spec["services"][sid]["task_id"]
        return probe(
            sid,
            task,
            upstream,
            lambda service, payload: fixture_cli(
                task, payload, "baseline" if sid == failed else "gold"
            ),
        )

    report = summarize(replay(scenario_spec, grades(scenario_spec), compose))
    assert not report["services"][failed]["restored"]
    assert report["services"][failed]["failed_probes"] == 1


def test_local_concurrency_suite_still_required_for_reservation():
    scenario = spec()
    called = []

    def compose(sid, evidence, upstream):
        called.append(sid)
        return successful_probe(sid, evidence, upstream)

    report = summarize(
        replay(scenario, grades(scenario, failed={"reservation"}), compose)
    )
    assert "reservation" not in called
    assert report["services"]["reservation"]["workflow"] == "REPAIR_READY"
    assert report["services"]["reservation"]["not_restored_seconds"] == 240


def test_downstream_only_missing_services_remain_in_denominator():
    scenario = spec()
    available = [
        g for g in grades(scenario) if g["service"] in {"release", "reservation"}
    ]
    report = summarize(replay(scenario, available, successful_probe))
    assert report["verified_rate"] == 2 / 8
    assert report["restored_rate"] == 0
    assert report["services"]["journal"]["not_submitted"]
    assert all(s["not_restored_seconds"] == 240 for s in report["services"].values())


def test_cache_and_buffer_expiration_without_patches():
    report = summarize(replay(spec("DC02"), [], successful_probe))
    assert report["services"]["telemetry"]["capability_seconds"] == {
        "buffered": 120,
        "offline": 120,
    }
    assert report["services"]["release"]["capability_seconds"] == {
        "limited": 180,
        "blocked_safe": 60,
    }
    assert report["services"]["release"]["unavailable_seconds"] == 60


def test_expiration_does_not_revoke_new_verified_alternate_path():
    scenario = spec("DC02")
    report = summarize(replay(scenario, grades(scenario, at=30), successful_probe))
    assert report["restored_rate"] == 1
    assert (
        report["services"]["release"]["capability_seconds"].get("blocked_safe", 0) == 0
    )


def test_fact_flip_invalidates_and_reprobes_every_descendant():
    scenario = spec()
    scenario["author_environment_events"] = [
        dict(at_seconds=10, event="observed_fact", fact="source_complete", value=False),
        dict(at_seconds=30, event="observed_fact", fact="source_complete", value=True),
    ]
    events = replay(scenario, grades(scenario), successful_probe, horizon=40)
    report = summarize(events)
    assert all(s["not_restored_seconds"] == 20 for s in report["services"].values())
    assert sum(e["kind"] == "probed" for e in events) == 16
    assert report["services"]["journal"]["environment_blocked_seconds"] == 20


def test_new_failed_patch_invalidates_successful_downstream():
    scenario = spec()
    repair = grades(scenario)
    changed = dict(repair[0], at_seconds=20, patch_sha256="f" * 64, resolved=False)
    report = summarize(
        replay(scenario, repair + [changed], successful_probe, horizon=40)
    )
    assert report["restored_rate"] == 0
    assert all(s["not_restored_seconds"] == 20 for s in report["services"].values())


def test_receipt_edit_and_truncation_rejected(tmp_path):
    path = tmp_path / "events.jsonl"
    replay(spec(), [], successful_probe, log=EventLog("trial", "DC01", path))
    original = path.read_text()
    path.write_text(original.replace('"trial_id": "trial"', '"trial_id": "other"', 1))
    with pytest.raises(ValueError, match="chain"):
        read_events(path)
    path.write_text(original.splitlines()[0] + "\n")
    with pytest.raises(ValueError, match="Incomplete"):
        read_events(path)


def test_summary_checks_receipt_chain_without_file_roundtrip():
    events = replay(spec(), [], successful_probe)
    events[-1]["seconds"] += 1
    with pytest.raises(ValueError, match="chain"):
        summarize(events)


@pytest.mark.parametrize("corruption", ["restart", "scenario", "start_time"])
def test_valid_hashes_do_not_allow_invalid_trial_boundaries(corruption):
    original = replay(spec(), [], successful_probe)
    log = EventLog("test", "DC01")
    first = original[0]["payload"]
    if corruption == "scenario":
        first["scenario"]["scenario_id"] = "DC02"
    log.append(1 if corruption == "start_time" else 0, "started", first)
    if corruption == "restart":
        log.append(10, "started", first)
    log.append(240, "finished", original[-1]["payload"])
    with pytest.raises(ValueError, match="boundaries"):
        summarize(log.events)


@pytest.mark.parametrize("invalid", [-1, float("nan"), float("inf"), True])
def test_invalid_clock_rejected(invalid):
    with pytest.raises(ValueError, match="seconds"):
        replay(spec(), [], successful_probe, horizon=invalid)


def test_standard_predictions_accept_mapping_and_jsonl(tmp_path):
    row = dict(
        instance_id="tsmc__f01-v0.2",
        model_name_or_path="future-api-harness",
        model_patch="patch",
    )
    for name, value in [
        ("preds.json", json.dumps({row["instance_id"]: row})),
        ("preds.jsonl", json.dumps(row) + "\n"),
    ]:
        path = tmp_path / name
        path.write_text(value)
        assert predictions_from(path) == {row["instance_id"]: row}
    path.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="Duplicate"):
        predictions_from(path)


@pytest.mark.parametrize(
    "bad_result",
    [
        {"passed": True},
        {"passed": True, "artifact": []},
        {"passed": True, "artifact": {"value": float("nan")}},
    ],
)
def test_malformed_probe_cannot_restore_or_abort_other_services(bad_result):
    scenario = spec("DC02")

    def compose(sid, evidence, upstream):
        return (
            bad_result
            if sid == "workers"
            else successful_probe(sid, evidence, upstream)
        )

    events = replay(scenario, grades(scenario), compose)
    report = summarize(events)
    assert not report["services"]["workers"]["restored"]
    assert report["services"]["workers"]["failed_probes"] == 1
    assert report["services"]["maintenance"]["restored"]


def test_all_observations_at_one_timestamp_precede_probing():
    scenario = spec("DC04")
    scenario["author_environment_events"] = [
        dict(at_seconds=60, event="observed_fact", fact="source_complete", value=True),
        dict(at_seconds=60, event="observed_fact", fact="source_complete", value=False),
    ]
    report = summarize(replay(scenario, grades(scenario), successful_probe))
    assert report["services"]["journal"]["first_restored_seconds"] is None
    assert report["first_all_protected_restored_seconds"] is None


def test_probe_callback_cannot_mutate_recorded_evidence():
    scenario = spec()

    def compose(sid, evidence, upstream):
        evidence["patch"] = "f" * 64
        return successful_probe(sid, evidence, upstream)

    report = summarize(replay(scenario, grades(scenario), compose))
    assert report["restored_rate"] == 1


def test_reservation_probe_rejects_extra_results():
    upstream = {
        "release": {"requests": [dict(id="good@safe", machine="safe", units=1)]}
    }
    result = probe(
        "reservation",
        "R02",
        upstream,
        lambda sid, payload: {
            "accepted": [True, True],
            "used": {"safe": 1, "locked": 0, "revoked": 0},
        },
    )
    assert not result["passed"]


@pytest.mark.parametrize(
    "task,output", [("F01", [0, 1, 0, 0]), ("F02", [1, 1, 1, 1, 1, 0])]
)
def test_boolean_contract_rejects_integer_results(task, output):
    assert not probe("test", task, {}, lambda sid, payload: output)["passed"]


def test_alarm_probe_honors_public_absolute_tolerance():
    output = [
        dict(sensor_id="p", status="ALARM", value_base=2000.0 + 1e-10),
        dict(sensor_id="p", status="ALARM", value_base=2000.0),
        dict(sensor_id="p", status="INVALID", value_base=None),
        dict(sensor_id="p", status="MISSING", value_base=None),
    ]
    assert probe("alarm", "F04", {}, lambda sid, payload: output)["passed"]


def test_alarm_probe_rejects_numeric_invalid_measurement():
    output = [dict(sensor_id="p", status="ALARM", value_base=2000.0)] * 2 + [
        dict(sensor_id="p", status="INVALID", value_base=2000.0),
        dict(sensor_id="p", status="MISSING", value_base=2000.0),
    ]
    assert not probe("alarm", "F04", {}, lambda sid, payload: output)["passed"]


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [None],
        [dict(instance_id="a", model_patch=None)],
        {"a": dict(instance_id="b", model_patch="patch")},
        [dict(instance_id="", model_patch="patch")],
        [dict(instance_id="a", model_patch="patch", model_name_or_path=["model"])],
    ],
)
def test_malformed_predictions_are_rejected_with_a_useful_error(tmp_path, payload):
    path = tmp_path / "predictions.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="[Pp]rediction"):
        predictions_from(path)


def test_duplicate_json_mapping_key_is_not_silently_overwritten(tmp_path):
    path = tmp_path / "predictions.json"
    path.write_text('{"a":{"model_patch":"first"},"a":{"model_patch":"second"}}')
    with pytest.raises(ValueError, match="[Dd]uplicate"):
        predictions_from(path)
