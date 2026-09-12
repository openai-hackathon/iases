"""Append-only receipts written by the host driver, outside candidate containers.

The hash chain detects accidental edits. It is not a signature or authentication
against someone who can rewrite the host's complete trial directory.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from swebench.benchmarks.tsmc.jsonio import decode_json


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def seconds(value):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError("Expected finite nonnegative seconds")
    return float(value)


class EventLog:
    def __init__(self, trial_id, scenario_id, path: Path | None = None):
        self.trial_id, self.scenario_id, self.path = trial_id, scenario_id, path
        self.events = []
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.open("x").close()

    def append(self, at, kind, payload):
        at = seconds(at)
        if self.events and at < self.events[-1]["seconds"]:
            raise ValueError("Event clock moved backwards")
        event = dict(
            schema="tsmc-receipt/1",
            trial_id=self.trial_id,
            scenario_id=self.scenario_id,
            sequence=len(self.events),
            seconds=at,
            kind=kind,
            payload=payload,
            previous=self.events[-1]["sha256"] if self.events else None,
        )
        event["sha256"] = digest(event)
        # Detach nested objects from the driver's mutable state.
        event = json.loads(json.dumps(event, allow_nan=False))
        if self.path:
            with self.path.open("a") as stream:
                stream.write(json.dumps(event, sort_keys=True, allow_nan=False) + "\n")
        self.events.append(event)
        return event


def read_events(path: Path):
    events = [
        decode_json(line, f"receipt at {path}:{index}")
        for index, line in enumerate(path.read_text().splitlines(), 1)
        if line.strip()
    ]
    validate_events(events)
    return events


def validate_events(events):
    if not isinstance(events, list) or not events:
        raise ValueError("Incomplete trial receipt log")
    previous, at, identity = None, 0, None
    for index, event in enumerate(events):
        if (
            not isinstance(event, dict)
            or not {
                "schema",
                "trial_id",
                "scenario_id",
                "sequence",
                "seconds",
                "kind",
                "payload",
                "previous",
                "sha256",
            }
            <= event.keys()
        ):
            raise ValueError(f"Malformed receipt at event {index}")
        encoded = {k: v for k, v in event.items() if k != "sha256"}
        current_identity = (event["trial_id"], event["scenario_id"])
        identity = identity or current_identity
        if (
            event["schema"] != "tsmc-receipt/1"
            or any(
                not isinstance(value, str) or not value for value in current_identity
            )
            or not isinstance(event["kind"], str)
            or not isinstance(event["payload"], dict)
            or type(event["sequence"]) is not int
            or current_identity != identity
            or event["sequence"] != index
            or event["previous"] != previous
            or event["sha256"] != digest(encoded)
            or seconds(event["seconds"]) < at
        ):
            raise ValueError(f"Invalid receipt chain at event {index}")
        previous, at = event["sha256"], event["seconds"]
    if not events or events[0]["kind"] != "started" or events[-1]["kind"] != "finished":
        raise ValueError("Incomplete trial receipt log")
    first = events[0]["payload"]
    if (
        events[0]["seconds"] != 0
        or not isinstance(first.get("scenario"), dict)
        or first["scenario"].get("scenario_id") != events[0]["scenario_id"]
        or first.get("mode") != "precomputed-patch-replay"
        or any(event["kind"] in {"started", "finished"} for event in events[1:-1])
        or seconds(first.get("horizon")) != events[-1]["seconds"]
    ):
        raise ValueError("Invalid trial receipt boundaries")
