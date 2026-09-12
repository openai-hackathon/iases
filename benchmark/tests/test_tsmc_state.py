import json
from pathlib import Path
import pytest
from swebench.benchmarks.tsmc.scenario.state import RecoveryState, validate

ROOT = Path(__file__).resolve().parents[1] / "benchmarks" / "tsmc"


def spec(id="DC01"):
    return json.loads(
        (ROOT / "scenarios" / "author" / id / "scenario.json").read_text()
    )


def mark_all(st):
    for i, sid in enumerate(st.states):
        st.record_patch(sid, f"{i + 1:064x}", True)


def activate(st, sid):
    assert st.restore(sid, st.probe_snapshot(sid), True)


@pytest.mark.parametrize("id", ["DC01", "DC02", "DC03", "DC04"])
def test_each_manifest_valid(id):
    validate(spec(id))


@pytest.mark.parametrize("id", ["DC01", "DC02", "DC03", "DC04"])
def test_all_local_repairs_can_start_without_dependencies(id):
    st = RecoveryState(spec(id))
    assert all(st.status(s) == "REPAIR_READY" for s in st.states)


@pytest.mark.parametrize("id", ["DC01", "DC02", "DC03", "DC04"])
def test_eventually_recovers_when_facts_and_current_probes_pass(id):
    st = RecoveryState(spec(id))
    mark_all(st)
    for k in st.facts:
        st.set_fact(k, True)
    for _ in range(len(st.states)):
        for s in st.states:
            if st.status(s) == "PROBE_READY":
                activate(st, s)
    assert all(x["active"] for x in st.states.values())


def test_repair_does_not_grant_service_recovery():
    st = RecoveryState(spec())
    st.record_patch("release", "a" * 64, True)
    assert st.status("release") == "WAITING_FOR_DEPENDENCIES"
    assert not st.states["release"]["active"]


def test_local_failed_cannot_probe():
    st = RecoveryState(spec())
    st.record_patch("journal", "a" * 64, False)
    with pytest.raises(ValueError):
        st.probe_snapshot("journal")


def test_failed_integration_not_recovered():
    st = RecoveryState(spec())
    mark_all(st)
    ev = st.probe_snapshot("journal")
    assert not st.restore("journal", ev, False)
    assert st.status("journal") == "PROBE_READY"


def test_multiple_valid_relative_orders():
    for order in [("state", "qualification"), ("qualification", "state")]:
        st = RecoveryState(spec())
        mark_all(st)
        activate(st, "journal")
        for sid in order:
            activate(st, sid)
        activate(st, "release")
        activate(st, "reservation")
        assert st.states["reservation"]["active"]


def test_incomparable_services_remain_incomparable():
    s = spec()
    pairs = {(p["higher"], p["lower"]) for p in s["importance"]}
    assert ("state", "qualification") not in pairs and (
        "qualification",
        "state",
    ) not in pairs


def test_soft_importance_is_not_hard_precedence():
    st = RecoveryState(spec())
    mark_all(st)
    activate(st, "journal")
    activate(st, "maintenance")
    assert not st.states["release"]["active"]
    assert st.states["maintenance"]["active"]


def test_high_importance_does_not_bypass_required_facts():
    st = RecoveryState(spec())
    mark_all(st)
    for sid in ["journal", "state", "qualification"]:
        activate(st, sid)
    st.set_fact("local_interlock_ok", False)
    assert not st.eligible_for_probe("release")


def test_primary_datacenter_need_not_recover_for_alternate_path():
    st = RecoveryState(spec())
    mark_all(st)
    for sid in ["journal", "state", "qualification", "release", "reservation"]:
        activate(st, sid)
    assert st.facts["dc_a_primary_up"] is False
    assert st.states["reservation"]["active"]


def test_shared_dependency_donation_is_a_set():
    st = RecoveryState(spec())
    assert st.blocked_business_dependents("journal") == {"release", "reservation"}


def test_dependency_loss_invalidates_descendants():
    st = RecoveryState(spec())
    mark_all(st)
    for sid in ["journal", "state", "qualification", "release", "reservation"]:
        activate(st, sid)
    st.invalidate_service("qualification")
    assert not st.states["release"]["active"] and not st.states["reservation"]["active"]
    assert st.states["state"]["active"]


def test_current_candidate_hash_bound_to_evidence():
    st = RecoveryState(spec())
    mark_all(st)
    ev = st.probe_snapshot("journal")
    st.record_patch("journal", "f" * 64, True)
    assert not st.restore("journal", ev, True)


def test_fact_changed_and_changed_back_rejects_old_evidence():
    st = RecoveryState(spec())
    mark_all(st)
    ev = st.probe_snapshot("journal")
    st.set_fact("source_complete", False)
    st.set_fact("source_complete", True)
    assert not st.restore("journal", ev, True)


def test_upstream_recovery_epoch_rejects_old_evidence():
    st = RecoveryState(spec())
    mark_all(st)
    for sid in ["journal", "state", "qualification"]:
        activate(st, sid)
    ev = st.probe_snapshot("release")
    st.invalidate_service("state")
    activate(st, "state")
    assert not st.restore("release", ev, True)


def test_wrong_scenario_evidence_rejected():
    st = RecoveryState(spec())
    mark_all(st)
    ev = st.probe_snapshot("journal")
    ev["scenario"] = "DC02"
    assert not st.restore("journal", ev, True)


def test_repeat_same_receipt_no_double_transition():
    st = RecoveryState(spec())
    mark_all(st)
    ev = st.probe_snapshot("journal")
    assert st.restore("journal", ev, True)
    epoch = st.states["journal"]["epoch"]
    assert st.restore("journal", ev, True)
    assert st.states["journal"]["epoch"] == epoch


def test_missing_source_is_not_repaired_by_code():
    st = RecoveryState(spec("DC04"))
    mark_all(st)
    assert not st.eligible_for_probe("journal")
    st.set_fact("source_complete", True)
    activate(st, "journal")
    assert st.states["journal"]["active"]


def test_all_fixed_but_environment_blocked_is_explicit():
    st = RecoveryState(spec("DC04"))
    mark_all(st)
    assert st.status("journal") == "WAITING_FOR_DEPENDENCIES"
    assert st.status("alarm") == "PROBE_READY"


def test_bad_sha_rejected():
    st = RecoveryState(spec())
    with pytest.raises(ValueError):
        st.record_patch("journal", "agent said fixed", True)


def test_dependency_cycle_rejected():
    s = spec()
    s["services"]["journal"]["restore_requires"] = ["release"]
    with pytest.raises(ValueError):
        validate(s)


def test_importance_cycle_rejected():
    s = spec()
    s["importance"].append(
        dict(higher="maintenance", lower="release", reason="contradiction")
    )
    with pytest.raises(ValueError):
        validate(s)


def test_unknown_service_rejected():
    s = spec()
    s["services"]["release"]["restore_requires"].append("fictional")
    with pytest.raises(ValueError):
        validate(s)


def test_unknown_fact_rejected():
    s = spec()
    s["services"]["release"]["restore_facts"].append("fictional")
    with pytest.raises(ValueError):
        validate(s)


def test_no_forced_total_order():
    s = spec()
    s["expected_total_order"] = ["journal", "release"]
    with pytest.raises(ValueError):
        validate(s)


def test_current_public_metadata_excludes_future_faults():
    for id in ["DC01", "DC02", "DC03", "DC04"]:
        assert "author_environment_events" not in json.loads(
            (ROOT / "scenarios" / "public" / f"{id}.json").read_text()
        )


def test_source_task_ids_exist_and_hashes_match():
    import hashlib

    for id in ["DC01", "DC02", "DC03", "DC04"]:
        refs = json.loads(
            (ROOT / "scenarios" / "author" / id / "source_map.json").read_text()
        )
        for item in refs.values():
            p = ROOT / "tasks" / item["task_id"] / "task.json"
            assert (
                hashlib.sha256(p.read_bytes()).hexdigest()
                == item["source_task_manifest_sha256"]
            )
