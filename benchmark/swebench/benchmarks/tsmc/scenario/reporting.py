"""Reconstruct recovery and integrate per-service time from saved receipts."""

from __future__ import annotations

from .engine import observation, transition
from .events import validate_events
from .state import RecoveryState


def summarize(events):
    validate_events(events)
    try:
        return _summarize(events)
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError(f"Malformed recovery receipt payload: {exc}") from exc


def _summarize(events):
    first = events[0]["payload"]
    state, expired = RecoveryState(first["scenario"]), set()
    totals = {
        sid: dict(
            task_id=cfg["task_id"],
            protected=cfg["protected_business_service"],
            not_restored_seconds=0.0,
            unavailable_seconds=0.0,
            untrusted_seconds=0.0,
            environment_blocked_seconds=0.0,
            capability_seconds={},
            first_restored_seconds=None,
            attempts=0,
            grade_wall_seconds=0.0,
            grade_queue_wall_seconds=0.0,
            timeouts=0,
            failed_probes=0,
        )
        for sid, cfg in state.spec["services"].items()
    }
    previous, all_protected = 0.0, None
    for event in events:
        at, payload, kind = event["seconds"], event["payload"], event["kind"]
        current = observation(state, expired)
        for sid, info in current["services"].items():
            duration, metric = at - previous, totals[sid]
            capability = info["capability"]
            metric["capability_seconds"][capability] = (
                metric["capability_seconds"].get(capability, 0) + duration
            )
            metric["not_restored_seconds"] += duration * (not info["active"])
            metric["unavailable_seconds"] += duration * (
                capability in {"offline", "blocked_safe"}
            )
            metric["untrusted_seconds"] += duration * (
                capability in {"unverified", "stale", "degraded"}
            )
            metric["environment_blocked_seconds"] += (
                duration * info["environment_blocked"]
            )
        if kind not in {"started", "finished"}:
            transition(state, expired, kind, payload)
        if payload["state"] != observation(state, expired):
            raise ValueError(
                f"Receipt state does not replay at event {event['sequence']}"
            )
        if kind == "graded":
            metric = totals[payload["service"]]
            metric["attempts"] += 1
            metric["grade_wall_seconds"] += payload.get("wall_seconds", 0)
            metric["grade_queue_wall_seconds"] += payload.get("queue_wall_seconds", 0)
            metric["timeouts"] += int(payload.get("timeout", False))
        if kind == "probed":
            metric = totals[payload["service"]]
            metric["failed_probes"] += int(not payload["passed"])
            if payload["restored"] and metric["first_restored_seconds"] is None:
                metric["first_restored_seconds"] = at
        for sid, value in state.states.items():
            totals[sid].update(
                verified=value["verified"],
                restored=value["active"],
                workflow=state.status(sid),
                not_submitted=totals[sid]["attempts"] == 0,
            )
        protected = [sid for sid, metric in totals.items() if metric["protected"]]
        if (
            protected
            and all(state.states[sid]["active"] for sid in protected)
            and all_protected is None
        ):
            all_protected = at
        previous = at
    if previous != first["horizon"]:
        raise ValueError("Trial did not reach its declared observation horizon")
    return dict(
        schema="tsmc-scenario-report/1",
        trial_id=events[0]["trial_id"],
        scenario_id=events[0]["scenario_id"],
        mode=first["mode"],
        horizon_seconds=previous,
        service_count=len(totals),
        verified_rate=sum(m["verified"] for m in totals.values()) / len(totals),
        restored_rate=sum(m["restored"] for m in totals.values()) / len(totals),
        first_all_protected_restored_seconds=all_protected,
        services=totals,
        final_state=observation(state, expired),
        timing_note="Replay availability and environment times are synthetic; grade wall times measure Docker evaluation, not agent repair.",
    )
