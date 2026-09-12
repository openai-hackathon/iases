"""Deterministic recovery replay over trusted grade and composition receipts."""

from __future__ import annotations

from copy import deepcopy
from itertools import groupby
import json

from .events import EventLog, digest, seconds
from .state import RecoveryState


def public_spec(spec):
    return {
        k: deepcopy(v)
        for k, v in spec.items()
        if k not in {"author_environment_events", "implementation_status"}
    }


def observation(state, expired):
    services = {}
    for sid, value in state.states.items():
        cfg = state.spec["services"][sid]
        capability = "available" if value["active"] else cfg["initial_state"]
        if not value["active"] and sid in expired:
            capability = (
                "offline" if cfg["dc_dependency"] == "buffered" else "blocked_safe"
            )
        services[sid] = {
            **value,
            "workflow": state.status(sid),
            "capability": capability,
            "environment_blocked": any(
                not state.facts[f] for f in cfg["restore_facts"]
            ),
        }
    return dict(
        facts=deepcopy(state.facts),
        fact_epochs=deepcopy(state.fact_epochs),
        services=services,
        expired=sorted(expired),
    )


def transition(state, expired, kind, payload):
    """Same reducer used by execution and report reconstruction."""
    if kind == "graded":
        state.record_patch(
            payload["service"], payload["patch_sha256"], payload["resolved"]
        )
    elif kind == "observed_fact":
        state.set_fact(payload["fact"], payload["value"])
    elif kind == "observed_grace_expired":
        sid = payload["service"]
        if sid not in state.states:
            raise ValueError("Unknown grace timer service")
        # This timer expires the initial fallback, not a newly verified path.
        expired.add(sid)
    elif kind == "invalidated":
        state.invalidate_service(payload["service"])
    elif kind == "probed":
        restored = state.restore(
            payload["service"], payload["evidence"], payload["passed"]
        )
        if restored != payload["restored"]:
            raise ValueError(
                "Probe receipt does not match current recovery prerequisites"
            )
    else:
        raise ValueError(f"Unsupported recovery event: {kind}")


def replay(spec, grades, probe, *, trial_id="replay", horizon=240, log=None):
    """Replay precomputed submissions; no synthetic duration is an agent measurement.

    Each grade contains a host-owned ``at_seconds`` availability time. The
    default CLI supplies all patches at time zero. Probes consume current direct
    upstream artifacts and run only after their required task grades pass.
    """
    horizon = seconds(horizon)
    state, expired, artifacts, attempted = RecoveryState(spec), set(), {}, set()
    log = log or EventLog(trial_id, spec["scenario_id"])
    if log.scenario_id != spec["scenario_id"] or log.events:
        raise ValueError("Replay requires a fresh log for the selected scenario")
    log.append(
        0,
        "started",
        dict(
            mode="precomputed-patch-replay",
            replay_order="observations-before-probes",
            horizon=horizon,
            scenario=public_spec(spec),
            state=observation(state, expired),
        ),
    )
    scheduled = []
    for event in spec.get("author_environment_events", []):
        kind = event["event"]
        if kind not in {"observed_fact", "observed_grace_expired", "invalidated"}:
            raise ValueError(f"Unknown author event: {kind}")
        scheduled.append(
            (
                seconds(event["at_seconds"]),
                0,
                kind,
                {k: v for k, v in event.items() if k not in {"at_seconds", "event"}},
            )
        )
    for grade in grades:
        scheduled.append(
            (
                seconds(grade["at_seconds"]),
                1,
                "graded",
                {k: v for k, v in grade.items() if k != "at_seconds"},
            )
        )

    def record(at, kind, payload):
        transition(state, expired, kind, payload)
        log.append(at, kind, {**payload, "state": observation(state, expired)})

    for at, batch in groupby(
        sorted(scheduled, key=lambda row: row[:2]), key=lambda row: row[0]
    ):
        if at > horizon:
            continue
        # Apply all observations and submissions at this instant before any
        # recovery decision. A same-time revocation must not trail a probe.
        for _, _, kind, payload in batch:
            record(at, kind, payload)
        for sid in list(artifacts):
            if not state.states[sid]["active"]:
                del artifacts[sid]
        while True:
            ready = [
                sid
                for sid in state.states
                if state.status(sid) == "PROBE_READY"
                and digest(state.probe_snapshot(sid)) not in attempted
            ]
            if not ready:
                break
            for sid in ready:
                evidence = state.probe_snapshot(sid)
                attempted.add(digest(evidence))
                upstream = {
                    d: deepcopy(artifacts[d])
                    for d in spec["services"][sid]["restore_requires"]
                }
                try:
                    result = probe(sid, deepcopy(evidence), upstream)
                    if (
                        not isinstance(result, dict)
                        or type(result.get("passed")) is not bool
                    ):
                        raise ValueError(
                            "Probe result must contain a boolean passed field"
                        )
                    if result["passed"] and not isinstance(
                        result.get("artifact"), dict
                    ):
                        raise ValueError(
                            "Passing probe result must contain an artifact object"
                        )
                    # Validate and detach the result before changing lifecycle
                    # state; malformed output must remain a failed probe.
                    result = json.loads(json.dumps(result, allow_nan=False))
                    passed = result["passed"]
                except Exception as exc:
                    result, passed = dict(error=f"{type(exc).__name__}: {exc}"), False
                receipt = dict(
                    service=sid,
                    task_id=spec["services"][sid]["task_id"],
                    patch_sha256=evidence["patch"],
                    evidence=evidence,
                    passed=passed,
                    restored=passed,
                    result=result,
                )
                record(at, "probed", receipt)
                if passed:
                    artifacts[sid] = deepcopy(result["artifact"])
    log.append(horizon, "finished", dict(state=observation(state, expired)))
    return log.events
