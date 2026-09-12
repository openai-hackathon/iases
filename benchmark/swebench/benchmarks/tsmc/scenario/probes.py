"""Executable synthetic data-flow contracts, using only candidate CLI outputs.

The caller supplies an isolated ``invoke(service, payload)`` implementation.
These probes supplement the required task suites; in particular the sequential
reservation CLI does not replace R02's concurrency tests.
"""

from __future__ import annotations

from copy import deepcopy
import math

CONTRACT_VERSION = "tsmc-composition/1.1"
MACHINES = ["safe", "locked", "revoked"]


def boolean_results(value, count):
    return (
        isinstance(value, list)
        and len(value) == count
        and all(type(item) is bool for item in value)
    )


def timestamp(minute):
    return f"2026-01-01T00:{minute:02d}:00Z"


def source_records():
    """Public deterministic incident fixture, with transport and domain sequences."""
    items = []

    def add(kind, payload):
        seq = len(items) + 1
        items.append(
            dict(
                sequence=seq,
                offset=seq,
                event_id=f"row-{seq}",
                event_time=timestamp(10 if seq % 2 else 9),
                value=1,
                machine_id="feed",
                kind=kind,
                payload=payload,
            )
        )

    for machine in MACHINES:
        add(
            "state",
            dict(
                machine_id=machine,
                sequence=41,
                new_state="LOCKED" if machine == "locked" else "AVAILABLE",
            ),
        )
    add("state", dict(machine_id="locked", sequence=40, new_state="AVAILABLE"))
    for machine in MACHINES:
        add(
            "qualification",
            dict(
                machine_id=machine, product_id="P", step_id="S", version=1, valid=True
            ),
        )
    add(
        "revocation",
        dict(machine_id="revoked", product_id="P", step_id="S", version=2, valid=False),
    )
    add("maintenance", dict(machine_id="locked", reason="inspect incident"))
    for start, end in [(0, 10), (5, 15)]:
        add(
            "downtime",
            dict(machine_id="locked", start=timestamp(start), end=timestamp(end)),
        )
    for _ in range(2):
        add(
            "step",
            dict(
                lot_id="impacted",
                machine_id="locked",
                enter=timestamp(0),
                exit=timestamp(20),
            ),
        )
    for event_id, start, end in [("incident-1", 5, 10), ("incident-2", 8, 15)]:
        add(
            "incident",
            dict(
                event_id=event_id,
                machine_id="locked",
                start=timestamp(start),
                end=timestamp(end),
            ),
        )
    for lot, results in [
        ("good", ["FAIL", "PASS"]),
        ("held", ["PASS"]),
        ("impacted", ["PASS"]),
        ("failed", ["PASS", "FAIL"]),
    ]:
        for index, result in enumerate(results):
            add(
                "wafer",
                dict(
                    lot_id=lot,
                    wafer_id="wafer-1",
                    test_id=f"test-{index}",
                    tested_at=timestamp(index),
                    valid=True,
                    result=result,
                ),
            )
    return items


def probe(service, task_id, upstream, invoke):
    """Return checks, candidate outputs and a downstream adapter artifact."""
    calls = []

    def call(payload):
        output = invoke(service, payload)
        calls.append(dict(input=payload, output=output))
        return output

    records = deepcopy(source_records())
    for dependency in ("telemetry", "journal"):
        if dependency in upstream:
            records = deepcopy(upstream[dependency]["records"])
            break

    def rows(kind):
        return [r["payload"] for r in records if r["kind"] == kind]

    checks, artifact = {}, {}
    if task_id == "R03":
        output = call(
            {
                "runs": [
                    dict(events=records, fail_at=2, crash_point="after_checkpoint"),
                    dict(events=records),
                    dict(events=records),
                ]
            }
        )
        checks = dict(
            complete_replay=output["outputs"] == records,
            durable_cursor=output["checkpoint"] == len(records),
            crash_exercised=output["failures"] == 1,
        )
        artifact = dict(records=output["outputs"])
    elif task_id == "R04":
        output = call(
            dict(
                limit=3,
                jobs=[
                    dict(outcome="error"),
                    dict(outcome="cancel"),
                    dict(outcome="ok", values=[1, 2]),
                ],
            )
        )
        checks = dict(
            slots_reclaimed=output["active"] == 0 and output["free_slots"] == 3,
            backlog_completed=output["results"]
            == [dict(status="error"), dict(status="cancelled"), dict(ok=3)],
        )
        artifact = dict(batch_size=output["free_slots"])
    elif task_id == "A04":
        width = upstream.get("workers", {}).get("batch_size", 3)
        if type(width) is not int or not 1 <= width <= 3:
            raise ValueError("Worker output did not supply bounded replay capacity")
        duplicate = {**records[0], "offset": len(records) + 1}
        batches = [records[n : n + width] for n in range(0, len(records), width)]
        output = call(dict(batches=batches + [records, [duplicate]]))
        batch = call(dict(batches=[records + [duplicate]]))
        expected_ids = {r["event_id"] for r in records}
        checks = dict(
            batch_incremental_equivalence=output == batch,
            no_late_event_loss=set(output["seen"]) == expected_ids,
            duplicate_invariance=output["totals"]
            == {"feed": dict(count=len(records), sum=float(len(records)))},
            offset_advanced=output["last_offset"] == len(records) + 1,
        )
        artifact = dict(
            records=[r for r in records if r["event_id"] in output["seen"]],
            aggregate=output,
        )
    elif task_id == "F03":
        output = call(dict(events=rows("state")))
        checks = dict(
            latest_state=output
            == {
                m: dict(sequence=41, state="LOCKED" if m == "locked" else "AVAILABLE")
                for m in MACHINES
            }
        )
        artifact = dict(machines=output)
    elif task_id == "F02":
        queries = [
            dict(op="query", machine_id=m, product_id="P", step_id="S")
            for m in MACHINES
        ]
        actions = (
            queries
            + [dict(op="update", record=r) for r in rows("revocation")]
            + queries
        )
        output = call(dict(qualifications=rows("qualification"), actions=actions))
        checks = dict(
            revocation_reflected=boolean_results(output, 6)
            and output == [True, True, True, True, True, False]
        )
        artifact = dict(
            qualifications=[
                dict(machine_id=m, product_id="P", step_id="S", valid=ok)
                for m, ok in zip(MACHINES, output[-3:])
            ]
        )
    elif task_id == "R01":
        payload = rows("maintenance")[0]
        request = dict(key="incident-order", payload=payload)
        output = call(
            dict(
                requests=[
                    {**request, "lose_response": True},
                    request,
                    request,
                    {**request, "payload": {**payload, "reason": "different"}},
                ]
            )
        )
        responses = output["responses"]
        checks = dict(
            one_order=output["work_orders"] == 1,
            durable_retry=responses[0] == dict(error="ConnectionError")
            and responses[1] == responses[2]
            and "ok" in responses[1],
            conflict_rejected=responses[3] == dict(error="ConflictError"),
        )
        artifact = dict(work_orders=output)
    elif task_id == "A01":
        output = call(
            dict(
                events=rows("downtime"),
                machine_id="locked",
                window_start=timestamp(0),
                window_end=timestamp(20),
            )
        )
        checks = dict(
            interval_union=output["downtime_seconds"] == 900,
            selected_window=output["window_seconds"] == 1200
            and output["downtime_fraction"] == 0.75,
        )
        artifact = dict(report=output)
    elif task_id == "A03":
        incidents = rows("incident")
        if "state" in upstream:
            machines = upstream["state"]["machines"]
            incidents = [
                e for e in incidents if machines[e["machine_id"]]["state"] == "LOCKED"
            ]
        output = call(dict(steps=rows("step"), events=incidents))
        checks = dict(
            exact_evidence=output
            == [dict(lot_id="impacted", event_ids=["incident-1", "incident-2"])]
        )
        artifact = dict(impacted=output)
    elif task_id == "A02":
        lots = ["good", "held", "impacted", "failed"]
        output = call(dict(rows=rows("wafer"), lot_ids=lots))
        expected = [
            dict(
                lot_id=lot,
                wafer_count=1,
                passed=int(lot != "failed"),
                pass_ratio=float(lot != "failed"),
            )
            for lot in lots
        ]
        checks = dict(latest_valid_per_wafer=output == expected)
        artifact = dict(reports=output)
    elif task_id == "F04":
        output = call(
            dict(
                sensors={"p": dict(kind="pressure", high=1500)},
                readings=[
                    dict(sensor_id="p", unit="kPa", value=2),
                    dict(sensor_id="p", unit="Pa", value=2000),
                    dict(sensor_id="p", unit="C", value=1),
                    dict(sensor_id="p", unit="Pa", value=None),
                ],
            )
        )
        checks = dict(
            equivalent_units=isinstance(output, list)
            and len(output) == 4
            and all(
                isinstance(row, dict)
                and set(row) == {"sensor_id", "status", "value_base"}
                and row["sensor_id"] == "p"
                and row["status"] == "ALARM"
                and type(row["value_base"]) in {int, float}
                and math.isclose(row["value_base"], 2000.0, rel_tol=0, abs_tol=1e-9)
                for row in output[:2]
            ),
            invalid_distinct=isinstance(output, list)
            and output[2:]
            == [
                dict(sensor_id="p", status="INVALID", value_base=None),
                dict(sensor_id="p", status="MISSING", value_base=None),
            ],
        )
        artifact = dict(alarms=output)
    elif task_id == "F01":
        machines = upstream.get("state", {}).get(
            "machines",
            {
                m: dict(sequence=41, state="LOCKED" if m == "locked" else "AVAILABLE")
                for m in MACHINES
            },
        )
        qualifications = upstream.get("qualification", {}).get(
            "qualifications",
            [
                dict(machine_id=m, product_id="P", step_id="S", valid=m != "revoked")
                for m in MACHINES
            ],
        )
        lots = {
            lot: dict(
                status="WAITING",
                quality_hold=lot == "held",
                product_id="P",
                step_id="S",
            )
            for lot in ["good", "held", "impacted", "failed"]
        }
        assignments = [
            dict(lot_id=lot, machine_id=m)
            for lot, m in [
                ("held", "safe"),
                ("good", "safe"),
                ("good", "locked"),
                ("good", "revoked"),
            ]
        ]
        expected = [False, True, False, False]
        if "lineage" in upstream and "wafer_report" in upstream:
            impacted = {r["lot_id"] for r in upstream["lineage"]["impacted"]}
            reports = {r["lot_id"]: r for r in upstream["wafer_report"]["reports"]}
            for lot, value in lots.items():
                report = reports.get(lot, {})
                value["quality_hold"] |= (
                    lot in impacted or report.get("pass_ratio") != 1.0
                )
            assignments += [
                dict(lot_id=lot, machine_id="safe") for lot in ["impacted", "failed"]
            ]
            expected += [False, False]
        output = call(
            dict(
                lots=lots,
                machines=machines,
                qualifications=qualifications,
                assignments=assignments,
            )
        )
        checks = dict(
            eligible_positive_and_unsafe_negative=boolean_results(output, len(expected))
            and output == expected
        )
        artifact = dict(
            requests=[
                dict(
                    id=a["lot_id"] + "@" + a["machine_id"],
                    machine=a["machine_id"],
                    units=1,
                )
                for a, ok in zip(assignments, output)
                if ok
            ]
        )
    elif task_id == "R02":
        if "release" in upstream:
            requests = upstream["release"]["requests"]
            expected = ["good@safe"]
        else:
            machines = upstream["state"]["machines"]
            requests = [
                dict(id=f"dispatch-{m}-{i}", machine=m, units=1)
                for m in MACHINES
                if machines[m]["state"] == "AVAILABLE"
                for i in range(2)
            ]
            expected = ["dispatch-safe-0", "dispatch-revoked-0"]
        output = call(dict(capacities={m: 1 for m in MACHINES}, requests=requests))
        accepted = [r["id"] for r, ok in zip(requests, output["accepted"]) if ok]
        checks = dict(
            complete_boolean_results=boolean_results(output["accepted"], len(requests)),
            legal_reservations=accepted == expected,
            integer_usage=all(type(value) is int for value in output["used"].values()),
            bounded_usage=output["used"]
            == {
                m: int(
                    any(
                        r["machine"] == m and ok
                        for r, ok in zip(requests, output["accepted"])
                    )
                )
                for m in MACHINES
            },
        )
        artifact = dict(reservations=output)
    else:
        raise ValueError(f"No composition contract for {service}/{task_id}")
    return dict(
        contract_version=CONTRACT_VERSION,
        passed=bool(checks) and all(checks.values()),
        checks=checks,
        artifact=artifact,
        calls=calls,
    )
