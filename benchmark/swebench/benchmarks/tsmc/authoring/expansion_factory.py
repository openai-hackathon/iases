"""Four medium factory tasks from the later difficulty-policy cohort."""

from .easy import examples
from .schema import simple


def tasks():
    yield simple(
        "F21",
        "Invoice matching pools receipts from different purchase-order lines",
        "purchase_line_three_way_match",
        "orders maps line ids to ordered quantity. receipts contains line/quantity signed adjustments. "
        "invoices contains line/quantity with nonnegative quantities and is processed in order. Accept each "
        "invoice only if cumulative accepted quantity for that line stays <=ordered and <=net received. "
        "Unknown lines reject. Return accepted flags and billed quantities for every order line.",
        """
        def run(request):
            received = {}
            for receipt in request["receipts"]:
                key = receipt["line"]
                received[key] = received.get(key, 0) + receipt["quantity"]
            billed = dict.fromkeys(request["orders"], 0)
            accepted = []
            for invoice in request["invoices"]:
                key, quantity = invoice["line"], invoice["quantity"]
                valid = key in billed and billed[key] + quantity <= min(request["orders"][key], received.get(key, 0))
                if valid:
                    billed[key] += quantity
                accepted.append(valid)
            return dict(accepted=accepted, billed=billed)
        """,
        ("received.get(key, 0))", "sum(received.values()))"),
        {
            "ignores_order_limit": (
                'min(request["orders"][key], received.get(key, 0))',
                "received.get(key, 0)",
            ),
            "forgets_prior_invoices": ("billed[key] + quantity <=", "quantity <="),
        },
        examples(
            [
                (
                    n,
                    {
                        "orders": o,
                        "receipts": [dict(line=k, quantity=q) for k, q in r],
                        "invoices": [dict(line=k, quantity=q) for k, q in i],
                    },
                    dict(accepted=a, billed=b),
                )
                for n, o, r, i, a, b in [
                    ("empty", {}, [], [], [], {}),
                    ("one", {"a": 5}, [("a", 5)], [("a", 3)], [True], {"a": 3}),
                    (
                        "cross_line",
                        {"a": 5, "b": 5},
                        [("b", 5)],
                        [("a", 3)],
                        [False],
                        {"a": 0, "b": 0},
                    ),
                    ("unknown", {}, [], [("a", 1)], [False], {}),
                    ("over_order", {"a": 3}, [("a", 5)], [("a", 4)], [False], {"a": 0}),
                    (
                        "partial",
                        {"a": 5},
                        [("a", 5)],
                        [("a", 3), ("a", 3)],
                        [True, False],
                        {"a": 3},
                    ),
                    (
                        "reversal",
                        {"a": 5},
                        [("a", 5), ("a", -3)],
                        [("a", 3)],
                        [False],
                        {"a": 0},
                    ),
                    (
                        "unrelated_receipt",
                        {"a": 5},
                        [("z", 5)],
                        [("a", 3)],
                        [False],
                        {"a": 0},
                    ),
                    (
                        "two_lines",
                        {"a": 5, "b": 5},
                        [("a", 2), ("b", 5)],
                        [("a", 3), ("b", 5)],
                        [False, True],
                        {"a": 0, "b": 5},
                    ),
                    (
                        "exact",
                        {"a": 5},
                        [("a", 2), ("a", 3)],
                        [("a", 2), ("a", 3)],
                        [True, True],
                        {"a": 5},
                    ),
                ]
            ]
        ),
        ("bpi-2019",),
        difficulty="medium",
        difficulty_reason="Reconcile three records at purchase-line granularity while accounting for partial invoices.",
    )

    yield simple(
        "F22",
        "One department's release clears another department's quality hold",
        "independent_hold_authorities",
        "Process hold/release events with lot, source and positive version. For each lot/source retain "
        "the event with greatest version; equal or older events are ignored. A release clears only that "
        "source. Return every observed lot with its sorted active hold sources, including empty lists.",
        """
        def run(request):
            states = {}
            for event in request["events"]:
                key = (event["lot"], event["source"])
                if key not in states or event["version"] > states[key]["version"]:
                    states[key] = event
            lots = {e["lot"] for e in request["events"]}
            return {lot: sorted(e["source"] for e in states.values() if e["lot"] == lot and e["op"] == "hold") for lot in sorted(lots)}
        """,
        ('(event["lot"], event["source"])', 'event["lot"]'),
        {
            "accepts_stale": ('event["version"] > states[key]["version"]', "True"),
            "equal_overwrites": (
                'event["version"] > states[key]["version"]',
                'event["version"] >= states[key]["version"]',
            ),
        },
        examples(
            [
                (
                    n,
                    {
                        "events": [
                            dict(lot=lot, source=s, version=v, op=o)
                            for lot, s, v, o in rows
                        ]
                    },
                    expected,
                )
                for n, rows, expected in [
                    ("empty", [], {}),
                    ("one", [("a", "qa", 1, "hold")], {"a": ["qa"]}),
                    (
                        "two_sources",
                        [("a", "qa", 1, "hold"), ("a", "eng", 1, "hold")],
                        {"a": ["eng", "qa"]},
                    ),
                    (
                        "release",
                        [("a", "qa", 1, "hold"), ("a", "qa", 2, "release")],
                        {"a": []},
                    ),
                    (
                        "foreign_release",
                        [("a", "qa", 1, "hold"), ("a", "eng", 2, "release")],
                        {"a": ["qa"]},
                    ),
                    (
                        "stale",
                        [("a", "qa", 2, "hold"), ("a", "qa", 1, "release")],
                        {"a": ["qa"]},
                    ),
                    (
                        "equal",
                        [("a", "qa", 1, "hold"), ("a", "qa", 1, "release")],
                        {"a": ["qa"]},
                    ),
                    (
                        "other_lot",
                        [("a", "qa", 1, "hold"), ("b", "qa", 1, "release")],
                        {"a": ["qa"], "b": []},
                    ),
                    (
                        "rehold",
                        [("a", "qa", 2, "release"), ("a", "qa", 3, "hold")],
                        {"a": ["qa"]},
                    ),
                    (
                        "one_remaining",
                        [
                            ("a", "qa", 1, "hold"),
                            ("a", "eng", 1, "hold"),
                            ("a", "qa", 2, "release"),
                        ],
                        {"a": ["eng"]},
                    ),
                ]
            ]
        ),
        ("production-log",),
        difficulty="medium",
        difficulty_reason="Track independent authority versions so one release cannot erase another hold.",
    )

    yield simple(
        "F23",
        "Dispatch schedules ignore dependency completion times",
        "precedence_resource_list_schedule",
        "jobs is a DAG in arbitrary order, with unique id, one resource, nonnegative duration and depends "
        "ids. Repeatedly choose the lexicographically smallest job whose dependencies have been scheduled. "
        "Start at max(resource availability, dependency finish times, release time). Resources start free "
        "at zero. Return jobs sorted by id with [start,end]. This is deterministic list scheduling, not "
        "makespan optimization. Reject cyclic graphs with ValueError.",
        """
        def run(request):
            pending = {j["id"]: j for j in request["jobs"]}
            schedule, available = {}, {}
            while pending:
                ready = sorted(k for k, j in pending.items() if all(d in schedule for d in j["depends"]))
                if not ready:
                    raise ValueError("cyclic dependencies")
                key = ready[0]
                job = pending.pop(key)
                start = max([job["release"], available.get(job["resource"], 0)] + [schedule[d][1] for d in job["depends"]])
                end = start + job["duration"]
                schedule[key] = [start, end]
                available[job["resource"]] = end
            return dict(sorted(schedule.items()))
        """,
        (
            '[schedule[d][1] for d in job["depends"]]',
            '[schedule[d][0] for d in job["depends"]]',
        ),
        {
            "ignores_resource": ('available.get(job["resource"], 0)', "0"),
            "ignores_release": ('[job["release"],', "[0,"),
        },
        examples(
            [
                (
                    n,
                    {
                        "jobs": [
                            dict(id=k, resource=r, duration=d, depends=deps, release=t)
                            for k, r, d, deps, t in rows
                        ]
                    },
                    v,
                )
                for n, rows, v in [
                    ("empty", [], {}),
                    ("single", [("a", "m", 3, [], 0)], {"a": [0, 3]}),
                    (
                        "dependency",
                        [("a", "m", 3, [], 0), ("b", "n", 2, ["a"], 0)],
                        {"a": [0, 3], "b": [3, 5]},
                    ),
                    (
                        "parallel",
                        [("a", "m", 3, [], 0), ("b", "n", 2, [], 0)],
                        {"a": [0, 3], "b": [0, 2]},
                    ),
                    (
                        "shared_resource",
                        [("a", "m", 3, [], 0), ("b", "m", 2, [], 0)],
                        {"a": [0, 3], "b": [3, 5]},
                    ),
                    ("release", [("a", "m", 3, [], 5)], {"a": [5, 8]}),
                    (
                        "reverse",
                        [("b", "n", 2, ["a"], 0), ("a", "m", 3, [], 0)],
                        {"a": [0, 3], "b": [3, 5]},
                    ),
                    (
                        "fan_in",
                        [
                            ("a", "m", 3, [], 0),
                            ("b", "n", 5, [], 0),
                            ("c", "q", 1, ["a", "b"], 0),
                        ],
                        {"a": [0, 3], "b": [0, 5], "c": [5, 6]},
                    ),
                    (
                        "zero_duration",
                        [("a", "m", 0, [], 4), ("b", "n", 2, ["a"], 0)],
                        {"a": [4, 4], "b": [4, 6]},
                    ),
                    (
                        "later_release",
                        [("a", "m", 3, [], 0), ("b", "n", 2, ["a"], 8)],
                        {"a": [0, 3], "b": [8, 10]},
                    ),
                ]
            ]
        ),
        ("production-log",),
        difficulty="medium",
        difficulty_reason="Coordinate dependency completion, resource serialization and release constraints.",
    )

    yield simple(
        "F24",
        "Revoked recipe approvals remain valid after revision replacement",
        "revision_bound_recipe_approval",
        "Process edit(revision), approve(revision,role), revoke(role), and activate events. Required roles "
        "are unique strings. An edit selects a new revision and clears approvals. Approve counts only for "
        "the current revision and a required role; revoke clears that role. Activate updates active revision "
        "only if all required roles currently approve. Return activation booleans and active (initially None).",
        """
        def run(request):
            current, active, approvals, results = None, None, set(), []
            for event in request["events"]:
                if event["op"] == "edit":
                    current = event["revision"]
                    approvals.clear()
                elif event["op"] == "approve":
                    if event["revision"] == current and event["role"] in request["roles"]:
                        approvals.add(event["role"])
                elif event["op"] == "revoke":
                    approvals.discard(event["role"])
                else:
                    valid = current is not None and set(request["roles"]) <= approvals
                    if valid:
                        active = current
                    results.append(valid)
            return dict(activations=results, active=active)
        """,
        ("approvals.clear()", "pass"),
        {
            "ignores_revision": ('event["revision"] == current and ', ""),
            "any_approval": ('set(request["roles"]) <= approvals', "bool(approvals)"),
        },
        examples(
            [
                (
                    n,
                    {"roles": ["qa", "eng"], "events": ev},
                    dict(activations=a, active=active),
                )
                for n, ev, a, active in [
                    ("empty", [], [], None),
                    ("no_revision", [{"op": "activate"}], [False], None),
                    (
                        "edit_clears",
                        [
                            {"op": "edit", "revision": 1},
                            {"op": "approve", "revision": 1, "role": "qa"},
                            {"op": "approve", "revision": 1, "role": "eng"},
                            {"op": "edit", "revision": 2},
                            {"op": "activate"},
                        ],
                        [False],
                        None,
                    ),
                    (
                        "partial",
                        [
                            {"op": "edit", "revision": 1},
                            {"op": "approve", "revision": 1, "role": "qa"},
                            {"op": "activate"},
                        ],
                        [False],
                        None,
                    ),
                    (
                        "valid",
                        [
                            {"op": "edit", "revision": 1},
                            {"op": "approve", "revision": 1, "role": "qa"},
                            {"op": "approve", "revision": 1, "role": "eng"},
                            {"op": "activate"},
                        ],
                        [True],
                        1,
                    ),
                    (
                        "stale_approval",
                        [
                            {"op": "edit", "revision": 2},
                            {"op": "approve", "revision": 1, "role": "qa"},
                            {"op": "approve", "revision": 2, "role": "eng"},
                            {"op": "activate"},
                        ],
                        [False],
                        None,
                    ),
                    (
                        "revoke",
                        [
                            {"op": "edit", "revision": 1},
                            {"op": "approve", "revision": 1, "role": "qa"},
                            {"op": "approve", "revision": 1, "role": "eng"},
                            {"op": "revoke", "role": "qa"},
                            {"op": "activate"},
                        ],
                        [False],
                        None,
                    ),
                    (
                        "retain_active",
                        [
                            {"op": "edit", "revision": 1},
                            {"op": "approve", "revision": 1, "role": "qa"},
                            {"op": "approve", "revision": 1, "role": "eng"},
                            {"op": "activate"},
                            {"op": "edit", "revision": 2},
                            {"op": "activate"},
                        ],
                        [True, False],
                        1,
                    ),
                    (
                        "foreign_role",
                        [
                            {"op": "edit", "revision": 1},
                            {"op": "approve", "revision": 1, "role": "ops"},
                            {"op": "activate"},
                        ],
                        [False],
                        None,
                    ),
                    (
                        "revision_zero",
                        [
                            {"op": "edit", "revision": 0},
                            {"op": "approve", "revision": 0, "role": "qa"},
                            {"op": "approve", "revision": 0, "role": "eng"},
                            {"op": "activate"},
                        ],
                        [True],
                        0,
                    ),
                ]
            ]
        ),
        ("nist-sms",),
        difficulty="medium",
        difficulty_reason="Invalidate approvals on edits while retaining the last successfully activated revision.",
    )
