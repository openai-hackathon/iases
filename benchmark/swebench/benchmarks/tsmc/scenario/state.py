"""Reference state model, not a live scheduler or security boundary.

Only a trusted grader/probe adapter may call record_patch/restore. Returned
snapshot tokens bind an integration result to the exact candidate and current
upstream/fact epochs. All task repair can start independently in local fixtures.
"""

from __future__ import annotations
from copy import deepcopy
import re
from typing import Any

from .events import seconds

TASKS = {f"{c}{i:02d}" for c in "FAR" for i in range(1, 5)}
STATES = {
    "unverified",
    "buffered",
    "stale",
    "blocked_safe",
    "offline",
    "backlog",
    "limited",
    "degraded",
}
DEPENDENCIES = {"hard", "buffered", "cache_grace", "async", "none"}


def _acyclic(nodes: set[str], edges: list[tuple[str, str]]) -> None:
    graph = {n: [] for n in nodes}
    for a, b in edges:
        if a not in nodes or b not in nodes:
            raise ValueError("unknown graph endpoint")
        graph[a].append(b)
    visiting: set[str] = set()
    done: set[str] = set()

    def visit(n: str) -> None:
        if n in visiting:
            raise ValueError("cycle detected")
        if n in done:
            return
        visiting.add(n)
        for m in graph[n]:
            visit(m)
        visiting.remove(n)
        done.add(n)

    for n in nodes:
        visit(n)


def validate(s: dict[str, Any]) -> None:
    if not isinstance(s, dict):
        raise ValueError("scenario must be an object")
    if s.get("schema_version") != "tsmc-incident/0.3":
        raise ValueError("unsupported schema")
    if s.get("synthetic") is not True:
        raise ValueError("synthetic flag required")
    if s.get("expected_total_order") is not None:
        raise ValueError("no fixed global order is allowed")
    if not isinstance(s.get("scenario_id"), str) or not s["scenario_id"]:
        raise ValueError("scenario_id must be a nonempty string")
    services = s.get("services")
    facts = s.get("environment_facts")
    if not isinstance(services, dict) or not services:
        raise ValueError("empty or invalid services")
    if not isinstance(facts, dict):
        raise ValueError("environment_facts must be an object")
    nodes = set(services)
    if not all(type(v) is bool for v in facts.values()):
        raise ValueError("facts must be bool")
    edges = []
    for sid, cfg in services.items():
        if not isinstance(sid, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", sid):
            raise ValueError("service names must be safe identifiers")
        if not isinstance(cfg, dict):
            raise ValueError("service configuration must be an object")
        if not isinstance(cfg.get("task_id"), str) or cfg["task_id"] not in TASKS:
            raise ValueError("unknown repair task")
        if (
            not isinstance(cfg.get("initial_state"), str)
            or cfg["initial_state"] not in STATES
        ):
            raise ValueError("bad initial state")
        if (
            not isinstance(cfg.get("dc_dependency"), str)
            or cfg["dc_dependency"] not in DEPENDENCIES
        ):
            raise ValueError("bad DC dependency")
        for field in ("repair_requires", "restore_requires", "restore_facts"):
            if not isinstance(cfg.get(field), list) or not all(
                isinstance(item, str) for item in cfg[field]
            ):
                raise ValueError(f"{sid}.{field} must be an array of names")
        if type(cfg.get("protected_business_service")) is not bool:
            raise ValueError("protected_business_service must be boolean")
        if cfg["repair_requires"]:
            raise ValueError("v0.3 local repair must not depend on service recovery")
        if len(cfg["restore_requires"]) != len(set(cfg["restore_requires"])):
            raise ValueError("duplicate dependency")
        if not set(cfg["restore_facts"]) <= set(facts):
            raise ValueError("unknown environment fact")
        edges.extend((dep, sid) for dep in cfg["restore_requires"])
    _acyclic(nodes, edges)
    importance = s.get("importance")
    if not isinstance(importance, list) or any(
        not isinstance(pair, dict)
        or not isinstance(pair.get("higher"), str)
        or not isinstance(pair.get("lower"), str)
        for pair in importance
    ):
        raise ValueError("importance must contain pairs of service names")
    _acyclic(nodes, [(p["higher"], p["lower"]) for p in s["importance"]])
    events = s.get("author_environment_events", [])
    if not isinstance(events, list):
        raise ValueError("author_environment_events must be an array")
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("environment event must be an object")
        seconds(event.get("at_seconds"))
        kind = event.get("event")
        if kind == "observed_fact":
            if (
                not isinstance(event.get("fact"), str)
                or event["fact"] not in facts
                or type(event.get("value")) is not bool
            ):
                raise ValueError(
                    "environment event contains an unknown fact or nonboolean value"
                )
        elif kind in {"observed_grace_expired", "invalidated"}:
            if (
                not isinstance(event.get("service"), str)
                or event["service"] not in services
            ):
                raise ValueError("environment event contains an unknown service")
        else:
            raise ValueError(f"unknown environment event: {kind}")


class RecoveryState:
    """Deterministic lifecycle validation over evidence supplied by trusted code.

    It does NOT execute hidden tests, authenticate events, compute partial-service
    utility, advance grace timers, submit requests, or implement scheduling policy.
    """

    def __init__(self, scenario: dict[str, Any]):
        validate(scenario)
        self.spec = deepcopy(scenario)
        self.facts = deepcopy(scenario["environment_facts"])
        self.fact_epochs = {k: 0 for k in self.facts}
        self.states = {
            k: dict(patch=None, verified=False, active=False, epoch=0)
            for k in scenario["services"]
        }

    def _descendants(self, sid: str) -> set[str]:
        if sid not in self.states:
            raise KeyError(sid)
        affected = {sid}
        changed = True
        while changed:
            changed = False
            for key, cfg in self.spec["services"].items():
                if key not in affected and affected.intersection(
                    cfg["restore_requires"]
                ):
                    affected.add(key)
                    changed = True
        return affected

    def _invalidate(self, affected: set[str]) -> None:
        for sid in affected:
            self.states[sid]["active"] = False
            self.states[sid]["epoch"] += 1

    def record_patch(self, sid: str, patch_sha256: str, passed: bool) -> None:
        if sid not in self.states:
            raise KeyError(sid)
        if not re.fullmatch(r"[0-9a-f]{64}", patch_sha256):
            raise ValueError("expected SHA256 hex")
        if type(passed) is not bool:
            raise ValueError("passed must be bool")
        st = self.states[sid]
        if st["patch"] == patch_sha256 and st["verified"] == passed:
            return
        self._invalidate(self._descendants(sid))
        st["patch"] = patch_sha256
        st["verified"] = passed

    def set_fact(self, key: str, value: bool) -> None:
        if key not in self.facts:
            raise KeyError(key)
        if type(value) is not bool:
            raise ValueError("fact must be bool")
        if self.facts[key] == value:
            return
        self.facts[key] = value
        self.fact_epochs[key] += 1
        affected = set()
        for sid, cfg in self.spec["services"].items():
            if key in cfg["restore_facts"]:
                affected |= self._descendants(sid)
        self._invalidate(affected)

    def invalidate_service(self, sid: str) -> None:
        self._invalidate(self._descendants(sid))

    def eligible_for_probe(self, sid: str) -> bool:
        cfg = self.spec["services"][sid]
        return bool(
            self.states[sid]["verified"]
            and all(self.states[d]["active"] for d in cfg["restore_requires"])
            and all(self.facts[f] for f in cfg["restore_facts"])
        )

    def probe_snapshot(self, sid: str) -> dict[str, Any]:
        if not self.eligible_for_probe(sid):
            raise ValueError("prerequisites not ready")
        cfg = self.spec["services"][sid]
        return dict(
            scenario=self.spec["scenario_id"],
            service=sid,
            patch=self.states[sid]["patch"],
            service_epoch=self.states[sid]["epoch"],
            upstream={d: self.states[d]["epoch"] for d in cfg["restore_requires"]},
            facts={f: self.fact_epochs[f] for f in cfg["restore_facts"]},
        )

    def restore(self, sid: str, evidence: dict[str, Any], probe_passed: bool) -> bool:
        if type(probe_passed) is not bool:
            raise ValueError("probe result must be bool")
        if not probe_passed or not self.eligible_for_probe(sid):
            return False
        if evidence != self.probe_snapshot(sid):
            return False
        # Repeating the same valid observation is idempotent.
        self.states[sid]["active"] = True
        return True

    def status(self, sid: str) -> str:
        if self.states[sid]["active"]:
            return "RESTORED"
        if not self.states[sid]["verified"]:
            return "REPAIR_READY"
        return (
            "PROBE_READY"
            if self.eligible_for_probe(sid)
            else "WAITING_FOR_DEPENDENCIES"
        )

    def blocked_business_dependents(self, sid: str) -> set[str]:
        """A set, not a fan-out multiplied score. No scheduling policy is imposed."""
        return {
            d
            for d in self._descendants(sid) - {sid}
            if self.spec["services"][d]["protected_business_service"]
            and not self.states[d]["active"]
        }
