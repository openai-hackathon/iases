"""Factory routing, scheduling, qualification and material accounting repairs."""

from .easy import examples
from .schema import simple


def tasks():
    yield simple(
        "F11",
        "Overlapping maintenance windows are subtracted twice",
        "maintenance_interval_union",
        "Return available integer minutes in [start,end) after subtracting the union of maintenance "
        "intervals. Intervals are [left,right), may overlap, repeat or lie outside the horizon; left<=right.",
        """
        def run(request):
            start, end = request["start"], request["end"]
            cursor, blocked = start, 0
            for left, right in sorted(request["maintenance"]):
                left, right = max(start, left, cursor), min(end, right)
                blocked += max(0, right - left)
                cursor = max(cursor, right)
            return end - start - blocked
        """,
        ("max(start, left, cursor)", "max(start, left)"),
        {
            "unclipped_end": ("min(end, right)", "right"),
            "drops_touching": ("right - left", "right - left - 1"),
        },
        examples(
            [
                (n, {"start": s, "end": e, "maintenance": m}, v)
                for n, s, e, m, v in [
                    ("empty", 0, 10, [], 10),
                    ("single", 0, 10, [[2, 4]], 8),
                    ("overlap", 0, 10, [[2, 6], [4, 8]], 4),
                    ("touching", 0, 10, [[2, 4], [4, 6]], 6),
                    ("duplicate", 0, 10, [[2, 6], [2, 6]], 6),
                    ("nested", 0, 10, [[1, 9], [3, 5]], 2),
                    ("clip", 3, 8, [[0, 4], [7, 10]], 3),
                    ("outside", 3, 8, [[0, 2], [9, 10]], 5),
                    ("zero", 4, 4, [[0, 8]], 0),
                    ("unsorted", 0, 10, [[6, 8], [1, 3], [2, 7]], 3),
                ]
            ]
        ),
        ("production-log",),
        difficulty="medium",
        difficulty_reason="Merge overlapping intervals before clipping and counting.",
    )

    yield simple(
        "F12",
        "Wildcard recipes override more specific equipment settings",
        "recipe_rule_specificity",
        "Rules match product and machine exactly or with '*'. Select the matching rule with most exact "
        "fields; ties use the greatest integer revision, then lexicographically smallest id. Return id or None.",
        """
        def run(request):
            matches = [r for r in request["rules"] if all(r[k] in ("*", request[k]) for k in ("product", "machine"))]
            def rank(rule):
                specificity = sum(rule[k] != "*" for k in ("product", "machine"))
                return (-specificity, -rule["revision"], rule["id"])
            return min(matches, key=rank)["id"] if matches else None
        """,
        (
            '(-specificity, -rule["revision"], rule["id"])',
            '(-rule["revision"], -specificity, rule["id"])',
        ),
        {
            "oldest_revision": ('-rule["revision"]', 'rule["revision"]'),
            "wrong_tie": ('rule["id"])', 'tuple(-ord(c) for c in rule["id"]))'),
        },
        examples(
            [
                (
                    n,
                    {
                        "product": "p",
                        "machine": "m",
                        "rules": [
                            dict(id=i, product=p, machine=m, revision=r)
                            for i, p, m, r in rules
                        ],
                    },
                    v,
                )
                for n, rules, v in [
                    ("empty", [], None),
                    ("single", [("a", "p", "m", 1)], "a"),
                    ("specific", [("a", "p", "m", 1), ("b", "*", "*", 9)], "a"),
                    ("unmatched", [("a", "q", "m", 1)], None),
                    ("one_field", [("a", "p", "*", 1), ("b", "*", "*", 9)], "a"),
                    ("revision", [("a", "p", "m", 1), ("b", "p", "m", 2)], "b"),
                    ("id_tie", [("b", "p", "m", 2), ("a", "p", "m", 2)], "a"),
                    ("machine_specific", [("a", "*", "m", 1), ("b", "*", "*", 8)], "a"),
                    ("specific_zero", [("a", "p", "m", 0), ("b", "p", "*", 4)], "a"),
                    ("fallback", [("a", "q", "m", 8), ("b", "*", "*", 1)], "b"),
                ]
            ]
        ),
        ("nist-sms",),
        difficulty="medium",
        difficulty_reason="Resolve a documented precedence order across three independent keys.",
    )

    yield simple(
        "F13",
        "Batch packing mixes incompatible reticles",
        "compatible_batch_packing",
        "Process lots in input order with first-fit packing. A batch can contain only equal product, recipe "
        "and reticle values, with summed units<=capacity. Each lot has 1..capacity units and a unique id. "
        "Return batches as lists of lot ids, preserving batch creation and insertion order.",
        """
        def run(request):
            batches = []
            for lot in request["lots"]:
                key = (lot["product"], lot["recipe"], lot["reticle"])
                for batch in batches:
                    if batch["key"] == key and batch["units"] + lot["units"] <= request["capacity"]:
                        batch["ids"].append(lot["id"])
                        batch["units"] += lot["units"]
                        break
                else:
                    batches.append(dict(key=key, units=lot["units"], ids=[lot["id"]]))
            return [b["ids"] for b in batches]
        """,
        (
            '(lot["product"], lot["recipe"], lot["reticle"])',
            '(lot["product"], lot["recipe"])',
        ),
        {
            "strict_capacity": ('<= request["capacity"]', '< request["capacity"]'),
            "ignores_recipe": (
                '(lot["product"], lot["recipe"], lot["reticle"])',
                '(lot["product"], lot["reticle"])',
            ),
        },
        examples(
            [
                (
                    n,
                    {
                        "capacity": 4,
                        "lots": [
                            dict(id=str(i), product=p, recipe=r, reticle=t, units=u)
                            for i, (p, r, t, u) in enumerate(rows)
                        ],
                    },
                    v,
                )
                for n, rows, v in [
                    ("empty", [], []),
                    ("single", [("p", "r", "t", 2)], [["0"]]),
                    (
                        "reticles",
                        [("p", "r", "a", 1), ("p", "r", "b", 1)],
                        [["0"], ["1"]],
                    ),
                    ("combine", [("p", "r", "t", 2), ("p", "r", "t", 2)], [["0", "1"]]),
                    (
                        "recipes",
                        [("p", "a", "t", 1), ("p", "b", "t", 1)],
                        [["0"], ["1"]],
                    ),
                    (
                        "products",
                        [("a", "r", "t", 1), ("b", "r", "t", 1)],
                        [["0"], ["1"]],
                    ),
                    ("full", [("p", "r", "t", 4), ("p", "r", "t", 1)], [["0"], ["1"]]),
                    (
                        "return_to_reticle",
                        [("p", "r", "a", 1), ("p", "r", "b", 1), ("p", "r", "a", 1)],
                        [["0", "2"], ["1"]],
                    ),
                    (
                        "first_fit",
                        [("p", "r", "t", 3), ("p", "r", "t", 2), ("p", "r", "t", 1)],
                        [["0", "2"], ["1"]],
                    ),
                    (
                        "three_reticles",
                        [("p", "r", "a", 1), ("p", "r", "b", 1), ("p", "r", "c", 1)],
                        [["0"], ["1"], ["2"]],
                    ),
                ]
            ]
        ),
        ("production-log",),
        difficulty="medium",
        difficulty_reason="Maintain first-fit state while enforcing compatibility and capacity.",
    )

    yield simple(
        "F14",
        "Setup planning assumes symmetric transition costs",
        "directed_setup_shortest_path",
        "Return the minimum setup cost from start to end in a directed graph of [from,to,cost] edges. "
        "Costs are nonnegative integers; nodes are strings. Return None if unreachable and zero for same node.",
        """
        import heapq
        def run(request):
            graph = {}
            for source, target, cost in request["edges"]:
                graph.setdefault(source, []).append((target, cost))
            queue = [(0, request["start"])]
            seen = set()
            while queue:
                distance, node = heapq.heappop(queue)
                if node in seen:
                    continue
                seen.add(node)
                if node == request["end"]:
                    return distance
                for target, cost in graph.get(node, []):
                    heapq.heappush(queue, (distance + cost, target))
            return None
        """,
        (
            "graph.setdefault(source, []).append((target, cost))",
            "graph.setdefault(source, []).append((target, cost))\n        graph.setdefault(target, []).append((source, cost))",
        ),
        {
            "unit_cost": ("distance + cost", "distance + 1"),
            "max_heap": ("distance + cost", "distance - cost"),
        },
        examples(
            [
                (n, {"start": s, "end": e, "edges": edges}, v)
                for n, s, e, edges, v in [
                    ("same", "a", "a", [], 0),
                    ("direct", "a", "b", [["a", "b", 4]], 4),
                    ("reverse", "b", "a", [["a", "b", 4]], None),
                    ("missing", "a", "c", [], None),
                    ("chain", "a", "c", [["a", "b", 2], ["b", "c", 3]], 5),
                    ("asymmetric", "b", "a", [["a", "b", 1], ["b", "a", 9]], 9),
                    (
                        "detour",
                        "a",
                        "c",
                        [["a", "c", 9], ["a", "b", 2], ["b", "c", 1]],
                        3,
                    ),
                    ("cycle", "c", "a", [["a", "b", 1], ["b", "c", 1]], None),
                    ("zero_edge", "a", "b", [["a", "b", 0]], 0),
                    ("parallel", "a", "b", [["a", "b", 8], ["a", "b", 3]], 3),
                ]
            ]
        ),
        ("production-log",),
        difficulty="medium",
        difficulty_reason="Respect directed transitions and multi-hop alternatives without looping on cycles.",
    )

    yield simple(
        "F15",
        "Rework visits consume the next route occurrence",
        "rework_visit_state_machine",
        "route contains unique operation names. events are pass/fail booleans for the currently active "
        "operation. A pass advances; a failure retries it up to max_retries failures, and the next failure "
        "scraps the lot. Retry count resets on advancement. Ignore events after done/scrap. Return "
        "{state: active/done/scrap, step: active operation or None, retries: current operation failures}.",
        """
        def run(request):
            position, retries, state = 0, 0, "active"
            route = request["route"]
            for passed in request["events"]:
                if state != "active" or position == len(route):
                    break
                if passed:
                    position += 1
                    retries = 0
                else:
                    retries += 1
                    if retries > request["max_retries"]:
                        state = "scrap"
            if state == "active" and position == len(route):
                state = "done"
            return dict(state=state, step=route[position] if state == "active" else None, retries=retries)
        """,
        ("retries = 0\n        else:", "retries = retries\n        else:"),
        {
            "early_scrap": (
                'retries > request["max_retries"]',
                'retries >= request["max_retries"]',
            ),
            "fail_advances": (
                "retries += 1",
                "retries += 1\n            position += 1",
            ),
        },
        examples(
            [
                (
                    n,
                    {"route": route, "max_retries": limit, "events": events},
                    dict(state=state, step=step, retries=r),
                )
                for n, route, limit, events, state, step, r in [
                    ("initial", ["a", "b"], 1, [], "active", "a", 0),
                    ("done", ["a"], 1, [True], "done", None, 0),
                    ("reset", ["a", "b"], 1, [False, True, False], "active", "b", 1),
                    ("scrap", ["a"], 1, [False, False], "scrap", None, 2),
                    ("reset_on_pass", ["a", "b"], 1, [False, True], "active", "b", 0),
                    ("empty", [], 1, [], "done", None, 0),
                    ("no_retry", ["a"], 0, [False], "scrap", None, 1),
                    ("extra_events", ["a"], 1, [True, False], "done", None, 0),
                    ("two_allowed", ["a"], 2, [False, False], "active", "a", 2),
                    (
                        "repeat_rework",
                        ["a", "b"],
                        1,
                        [False, True, False, True],
                        "done",
                        None,
                        0,
                    ),
                ]
            ]
        ),
        ("production-log",),
        difficulty="medium",
        difficulty_reason="Track retry lifetime separately from route progress and terminal states.",
    )

    yield simple(
        "F16",
        "Qualification windows compare local clock strings",
        "qualification_timezone_windows",
        "Each qualification has start/end ISO8601 timestamps with explicit offsets and an id. Return sorted "
        "ids valid at the supplied offset-aware at timestamp using start<=at<end in absolute time.",
        """
        from datetime import datetime
        def run(request):
            instant = datetime.fromisoformat(request["at"])
            def valid(row):
                start = datetime.fromisoformat(row["start"])
                end = datetime.fromisoformat(row["end"])
                return start <= instant < end
            return sorted(row["id"] for row in request["qualifications"] if valid(row))
        """,
        (
            "return start <= instant < end",
            "return start.replace(tzinfo=None) <= instant.replace(tzinfo=None) < end.replace(tzinfo=None)",
        ),
        {
            "includes_expiry": ("instant < end", "instant <= end"),
            "excludes_start": ("start <= instant", "start < instant"),
        },
        examples(
            [
                (n, {"at": at, "qualifications": [dict(id="q", start=s, end=e)]}, v)
                for n, at, s, e, v in [
                    (
                        "inside",
                        "2025-01-01T01:00+00:00",
                        "2025-01-01T00:00+00:00",
                        "2025-01-01T02:00+00:00",
                        ["q"],
                    ),
                    (
                        "outside",
                        "2025-01-01T03:00+00:00",
                        "2025-01-01T00:00+00:00",
                        "2025-01-01T02:00+00:00",
                        [],
                    ),
                    (
                        "offset",
                        "2025-01-01T09:00+08:00",
                        "2025-01-01T00:00+00:00",
                        "2025-01-01T02:00+00:00",
                        ["q"],
                    ),
                    (
                        "start",
                        "2025-01-01T00:00+00:00",
                        "2025-01-01T00:00+00:00",
                        "2025-01-01T02:00+00:00",
                        ["q"],
                    ),
                    (
                        "expiry",
                        "2025-01-01T02:00+00:00",
                        "2025-01-01T00:00+00:00",
                        "2025-01-01T02:00+00:00",
                        [],
                    ),
                    (
                        "previous_day",
                        "2024-12-31T20:00-05:00",
                        "2025-01-01T00:00+00:00",
                        "2025-01-01T02:00+00:00",
                        ["q"],
                    ),
                    (
                        "window_offset",
                        "2025-01-01T01:00+00:00",
                        "2025-01-01T08:00+08:00",
                        "2025-01-01T10:00+08:00",
                        ["q"],
                    ),
                    (
                        "same_wall",
                        "2025-01-01T01:00+08:00",
                        "2025-01-01T00:00+00:00",
                        "2025-01-01T02:00+00:00",
                        [],
                    ),
                    (
                        "offset_expiry",
                        "2025-01-01T10:00+08:00",
                        "2025-01-01T00:00+00:00",
                        "2025-01-01T02:00+00:00",
                        [],
                    ),
                    (
                        "zero_window",
                        "2025-01-01T00:00+00:00",
                        "2025-01-01T00:00+00:00",
                        "2025-01-01T00:00+00:00",
                        [],
                    ),
                ]
            ]
        ),
        ("production-log",),
        difficulty="medium",
        difficulty_reason="Normalize civil timestamps while preserving half-open validity boundaries.",
    )

    yield simple(
        "F17",
        "Partial reticle reservations consume stock on rejected orders",
        "atomic_multi_item_reservation",
        "stock maps item names to nonnegative counts. orders is a sequence of item/count dictionaries, with "
        "positive requested counts. Accept an order only if every item is available; deduct all or none. "
        "Missing items have zero stock. Return accepted booleans and final stock, preserving original keys.",
        """
        def run(request):
            stock = dict(request["stock"])
            accepted = []
            for order in request["orders"]:
                valid = all(stock.get(k, 0) >= n for k, n in order.items())
                if valid:
                    for key, amount in order.items():
                        stock[key] -= amount
                accepted.append(valid)
            return dict(accepted=accepted, stock=stock)
        """,
        ("if valid:", "if True:"),
        {
            "strict_stock": (">= n", "> n"),
            "checks_any": ("valid = all(", "valid = any("),
        },
        examples(
            [
                (n, {"stock": stock, "orders": orders}, {"accepted": a, "stock": v})
                for n, stock, orders, a, v in [
                    ("empty", {}, [], [], {}),
                    ("one", {"a": 3}, [{"a": 1}], [True], {"a": 2}),
                    (
                        "reject",
                        {"a": 1, "b": 0},
                        [{"a": 1, "b": 1}],
                        [False],
                        {"a": 1, "b": 0},
                    ),
                    ("exact", {"a": 1}, [{"a": 1}], [True], {"a": 0}),
                    (
                        "retry_after_reject",
                        {"a": 1, "b": 0},
                        [{"a": 1, "b": 1}, {"a": 1}],
                        [False, True],
                        {"a": 0, "b": 0},
                    ),
                    ("insufficient", {"a": 1}, [{"a": 2}], [False], {"a": 1}),
                    ("unknown", {"a": 1}, [{"z": 1}], [False], {"a": 1}),
                    ("empty_order", {"a": 1}, [{}], [True], {"a": 1}),
                    (
                        "deplete",
                        {"a": 2},
                        [{"a": 1}, {"a": 1}, {"a": 1}],
                        [True, True, False],
                        {"a": 0},
                    ),
                    (
                        "two_items",
                        {"a": 3, "b": 2},
                        [{"a": 1, "b": 2}],
                        [True],
                        {"a": 2, "b": 0},
                    ),
                ]
            ]
        ),
        ("bpi-2019",),
        difficulty="medium",
        difficulty_reason="Separate validation from mutation across all items and subsequent requests.",
    )

    yield simple(
        "F18",
        "Lot merge validation ignores quantities consumed by earlier operations",
        "lot_lineage_mass_balance",
        "stock maps unique lot ids to positive integer units. Each operation lists distinct input ids and "
        "an outputs mapping. Accept only existing inputs, new output ids, positive output quantities, and "
        "equal total units. On acceptance consume inputs and add outputs atomically. Return accepted and stock.",
        """
        def run(request):
            stock = dict(request["stock"])
            accepted = []
            for operation in request["operations"]:
                inputs, outputs = operation["inputs"], operation["outputs"]
                valid = (bool(inputs) and bool(outputs) and all(k in stock for k in inputs)
                         and all(k not in stock and n > 0 for k, n in outputs.items()))
                if valid:
                    valid = sum(stock[k] for k in inputs) == sum(outputs.values())
                if valid:
                    for key in inputs:
                        del stock[key]
                    stock.update(outputs)
                accepted.append(valid)
            return dict(accepted=accepted, stock=stock)
        """,
        (
            "sum(stock[k] for k in inputs) == sum(outputs.values())",
            "sum(stock[k] for k in inputs) >= sum(outputs.values())",
        ),
        {
            "allows_existing_output": ("k not in stock and n > 0", "n > 0"),
            "ignores_consumption": ("del stock[key]", "pass"),
        },
        examples(
            [
                (
                    n,
                    {
                        "stock": s,
                        "operations": [dict(inputs=i, outputs=o) for i, o in ops],
                    },
                    dict(accepted=a, stock=v),
                )
                for n, s, ops, a, v in [
                    ("empty", {"a": 4}, [], [], {"a": 4}),
                    (
                        "split",
                        {"a": 4},
                        [(["a"], {"b": 1, "c": 3})],
                        [True],
                        {"b": 1, "c": 3},
                    ),
                    ("loss", {"a": 4}, [(["a"], {"b": 3})], [False], {"a": 4}),
                    ("gain", {"a": 4}, [(["a"], {"b": 5})], [False], {"a": 4}),
                    (
                        "merge",
                        {"a": 1, "b": 3},
                        [(["a", "b"], {"c": 4})],
                        [True],
                        {"c": 4},
                    ),
                    (
                        "reuse",
                        {"a": 4},
                        [(["a"], {"b": 4}), (["a"], {"c": 4})],
                        [True, False],
                        {"b": 4},
                    ),
                    (
                        "collision",
                        {"a": 2, "b": 2},
                        [(["a"], {"b": 2})],
                        [False],
                        {"a": 2, "b": 2},
                    ),
                    (
                        "zero_output",
                        {"a": 4},
                        [(["a"], {"b": 4, "c": 0})],
                        [False],
                        {"a": 4},
                    ),
                    (
                        "small_loss",
                        {"a": 2, "b": 3},
                        [(["a", "b"], {"c": 4})],
                        [False],
                        {"a": 2, "b": 3},
                    ),
                    (
                        "chain",
                        {"a": 4},
                        [(["a"], {"b": 4}), (["b"], {"c": 4})],
                        [True, True],
                        {"c": 4},
                    ),
                ]
            ]
        ),
        ("production-log",),
        difficulty="medium",
        difficulty_reason="Preserve mass and identity through successive atomic lineage edits.",
    )
