"""Seven medium analytics tasks from the later difficulty-policy cohort."""

from .easy import examples
from .schema import simple


def tasks():
    yield simple(
        "A21",
        "Keyset pagination loses rows sharing the cursor timestamp",
        "composite_keyset_pagination",
        "rows contains unique id records with time and value. Sort by (time,id). cursor is None or a "
        "[time,id] exclusive lower bound. Return up to limit rows, with next_cursor equal to the last "
        "returned [time,id], or the input cursor when no rows return. limit>=1. Do not mutate input rows.",
        """
        def run(request):
            cursor = request["cursor"]
            rows = sorted(request["rows"], key=lambda r: (r["time"], r["id"]))
            rows = [r for r in rows if cursor is None or (r["time"], r["id"]) > tuple(cursor)]
            page = rows[:request["limit"]]
            return dict(rows=page, next_cursor=[page[-1]["time"], page[-1]["id"]] if page else cursor)
        """,
        ('(r["time"], r["id"]) > tuple(cursor)', 'r["time"] > cursor[0]'),
        {
            "inclusive_cursor": ("> tuple(cursor)", ">= tuple(cursor)"),
            "reversed_id_tie": (
                'key=lambda r: (r["time"], r["id"])',
                'key=lambda r: (r["time"], tuple(-ord(c) for c in r["id"]))',
            ),
        },
        examples(
            [
                (
                    n,
                    {
                        "rows": [dict(time=t, id=i, value=i) for t, i in rows],
                        "cursor": cursor,
                        "limit": limit,
                    },
                    dict(
                        rows=[dict(time=t, id=i, value=i) for t, i in expected],
                        next_cursor=next_cursor,
                    ),
                )
                for n, rows, cursor, limit, expected, next_cursor in [
                    ("empty", [], None, 2, [], None),
                    ("one", [(1, "a")], None, 2, [(1, "a")], [1, "a"]),
                    (
                        "same_time",
                        [(1, "a"), (1, "b")],
                        [1, "a"],
                        2,
                        [(1, "b")],
                        [1, "b"],
                    ),
                    ("later", [(1, "a"), (2, "b")], [1, "a"], 2, [(2, "b")], [2, "b"]),
                    ("tie_sort", [(1, "b"), (1, "a")], None, 1, [(1, "a")], [1, "a"]),
                    ("exclusive", [(1, "a")], [1, "a"], 2, [], [1, "a"]),
                    (
                        "limit",
                        [(1, "a"), (1, "b"), (1, "c")],
                        [1, "a"],
                        1,
                        [(1, "b")],
                        [1, "b"],
                    ),
                    ("missing_cursor", [(1, "c")], [1, "b"], 2, [(1, "c")], [1, "c"]),
                    (
                        "unsorted",
                        [(2, "a"), (1, "c"), (1, "a")],
                        [1, "b"],
                        2,
                        [(1, "c"), (2, "a")],
                        [2, "a"],
                    ),
                    ("beyond", [(1, "a")], [2, "z"], 2, [], [2, "z"]),
                ]
            ]
        ),
        ("nist-sms",),
        difficulty="medium",
        difficulty_reason="Keep a stable composite ordering across page boundaries and timestamp ties.",
    )

    yield simple(
        "A23",
        "Merged sensor summaries omit between-group variance",
        "parallel_variance_merge",
        "summaries contains count, mean and m2 (sum of squared deviations) for disjoint populations. "
        "Ignore zero-count groups. Return combined count, mean and population variance m2/count; an empty "
        "population returns mean=None, variance=None. Use the parallel variance formula with between-group "
        "mean correction. Test examples use exactly representable results.",
        """
        def run(request):
            count, mean, m2 = 0, 0.0, 0.0
            for group in request["summaries"]:
                n = group["count"]
                if not n:
                    continue
                total = count + n
                delta = group["mean"] - mean
                m2 += group["m2"] + delta * delta * count * n / total
                mean += delta * n / total
                count = total
            return dict(count=count, mean=mean if count else None, variance=m2 / count if count else None)
        """,
        (" + delta * delta * count * n / total", ""),
        {
            "unweighted_mean": ("delta * n / total", "delta / 2"),
            "sample_denominator": (
                "m2 / count if count else None",
                "m2 / max(1, count - 1) if count else None",
            ),
        },
        examples(
            [
                (
                    n,
                    {"summaries": [dict(count=c, mean=m, m2=s) for c, m, s in rows]},
                    dict(count=c, mean=m, variance=v),
                )
                for n, rows, c, m, v in [
                    ("empty", [], 0, None, None),
                    ("single", [(2, 2, 2)], 2, 2.0, 1.0),
                    ("different_means", [(1, 0, 0), (1, 4, 0)], 2, 2.0, 4.0),
                    ("equal_means", [(2, 2, 2), (2, 2, 2)], 4, 2.0, 1.0),
                    ("weighted", [(1, 0, 0), (3, 4, 0)], 4, 3.0, 3.0),
                    ("reverse_weighted", [(3, 4, 0), (1, 0, 0)], 4, 3.0, 3.0),
                    ("zero_group", [(0, 100, 0), (2, 2, 2)], 2, 2.0, 1.0),
                    ("negative", [(1, -2, 0), (1, 2, 0)], 2, 0.0, 4.0),
                    ("within_between", [(2, 0, 2), (2, 4, 2)], 4, 2.0, 5.0),
                    ("all_empty", [(0, 0, 0)], 0, None, None),
                ]
            ]
        ),
        ("zema-hydraulic",),
        difficulty="medium",
        difficulty_reason="Combine sufficient statistics using count weighting and the cross-group correction.",
    )

    yield simple(
        "A24",
        "Overlapping downtime causes are counted more than once",
        "exclusive_downtime_attribution",
        "Within integer horizon [start,end), assign each blocked minute to exactly one cause. intervals "
        "contains cause/start/end records with half-open bounds. priority lists all causes from highest "
        "to lowest. Return durations for every listed cause, including zero. Clip intervals to the horizon.",
        """
        def run(request):
            totals = dict.fromkeys(request["priority"], 0)
            for minute in range(request["start"], request["end"]):
                for cause in request["priority"]:
                    if any(r["cause"] == cause and r["start"] <= minute < r["end"] for r in request["intervals"]):
                        totals[cause] += 1
                        break
            return totals
        """,
        ("break\n    return", "pass\n    return"),
        {
            "low_priority_first": (
                'for cause in request["priority"]:',
                'for cause in reversed(request["priority"]):',
            ),
            "inclusive_end": ('minute < r["end"]', 'minute <= r["end"]'),
        },
        examples(
            [
                (
                    n,
                    {
                        "start": 0,
                        "end": 6,
                        "priority": ["safety", "maintenance"],
                        "intervals": [
                            dict(cause=c, start=s, end=e) for c, s, e in rows
                        ],
                    },
                    dict(safety=a, maintenance=b),
                )
                for n, rows, a, b in [
                    ("empty", [], 0, 0),
                    ("single", [("maintenance", 1, 3)], 0, 2),
                    ("overlap", [("safety", 2, 4), ("maintenance", 1, 5)], 2, 2),
                    ("disjoint", [("safety", 0, 2), ("maintenance", 3, 5)], 2, 2),
                    ("full_overlap", [("safety", 0, 6), ("maintenance", 0, 6)], 6, 0),
                    ("duplicate", [("safety", 1, 3), ("safety", 1, 3)], 2, 0),
                    ("clip", [("safety", -2, 2), ("maintenance", 4, 9)], 2, 2),
                    ("touching", [("safety", 0, 2), ("maintenance", 2, 4)], 2, 2),
                    ("empty_interval", [("safety", 2, 2)], 0, 0),
                    ("nested", [("maintenance", 0, 6), ("safety", 2, 3)], 1, 5),
                ]
            ]
        ),
        ("nist-sms",),
        difficulty="medium",
        difficulty_reason="Resolve overlapping causes by an exclusive precedence rule before computing downtime.",
    )

    yield simple(
        "A25",
        "Lineage impact analysis stops at the first generation",
        "transitive_material_descendants",
        "edges is a directed material lineage graph [parent,child], possibly cyclic or duplicated. "
        "Return sorted ids reachable from any seed through one or more edges, excluding the seed ids "
        "themselves. Unknown seeds produce no descendants. Traversal must terminate on cycles.",
        """
        def run(request):
            seeds = set(request["seeds"])
            seen, pending = set(seeds), list(seeds)
            while pending:
                parent = pending.pop()
                for source, target in request["edges"]:
                    if source == parent and target not in seen:
                        seen.add(target)
                        pending.append(target)
            return sorted(seen - seeds)
        """,
        ("pending.append(target)", "pass"),
        {
            "reverse_edges": (
                'for source, target in request["edges"]:',
                'for target, source in request["edges"]:',
            ),
            "includes_seeds": ("sorted(seen - seeds)", "sorted(seen)"),
        },
        examples(
            [
                (n, {"seeds": s, "edges": e}, v)
                for n, s, e, v in [
                    ("empty", [], [], []),
                    ("direct", ["a"], [["a", "b"]], ["b"]),
                    ("chain", ["a"], [["a", "b"], ["b", "c"]], ["b", "c"]),
                    ("unknown", ["z"], [["a", "b"]], []),
                    ("cycle", ["a"], [["a", "b"], ["b", "c"], ["c", "a"]], ["b", "c"]),
                    (
                        "diamond",
                        ["a"],
                        [["a", "b"], ["a", "c"], ["b", "d"], ["c", "d"]],
                        ["b", "c", "d"],
                    ),
                    ("multiple_seeds", ["a", "b"], [["a", "b"], ["b", "c"]], ["c"]),
                    ("self", ["a"], [["a", "a"]], []),
                    ("duplicate", ["a"], [["a", "b"], ["a", "b"]], ["b"]),
                    ("branch", ["a"], [["a", "b"], ["b", "d"], ["x", "z"]], ["b", "d"]),
                ]
            ]
        ),
        ("production-log",),
        difficulty="medium",
        difficulty_reason="Compute transitive material impact with cycle and duplicate protection.",
    )

    yield simple(
        "A26",
        "Deleted telemetry records reappear when older partitions are replayed",
        "versioned_tombstone_reconciliation",
        "records contains key/version/value/deleted records. version is a positive integer; versions are "
        "unique per key. Keep the greatest version for each key, including tombstones. Return only live "
        "key/value pairs sorted by key. Partition input order must not affect the result.",
        """
        def run(request):
            latest = {}
            for record in request["records"]:
                key = record["key"]
                if key not in latest or record["version"] > latest[key]["version"]:
                    latest[key] = record
            return {k: r["value"] for k, r in sorted(latest.items()) if not r["deleted"]}
        """,
        (
            "latest[key] = record",
            'if not record["deleted"]:\n                latest[key] = record',
        ),
        {
            "arrival_order": (
                'key not in latest or record["version"] > latest[key]["version"]',
                "True",
            ),
            "drops_zero": (
                'if not r["deleted"]}',
                'if not r["deleted"] and r["value"]}',
            ),
        },
        examples(
            [
                (
                    n,
                    {
                        "records": [
                            dict(key=k, version=v, value=x, deleted=d)
                            for k, v, x, d in rows
                        ]
                    },
                    expected,
                )
                for n, rows, expected in [
                    ("empty", [], {}),
                    ("one", [("a", 1, 2, False)], {"a": 2}),
                    ("delete", [("a", 1, 2, False), ("a", 2, None, True)], {}),
                    ("update", [("a", 1, 2, False), ("a", 2, 3, False)], {"a": 3}),
                    (
                        "replay_after_delete",
                        [("a", 2, None, True), ("a", 1, 2, False)],
                        {},
                    ),
                    ("old_update", [("a", 2, 3, False), ("a", 1, 2, False)], {"a": 3}),
                    ("zero", [("a", 1, 0, False)], {"a": 0}),
                    ("restore", [("a", 2, None, True), ("a", 3, 4, False)], {"a": 4}),
                    ("other_key", [("a", 1, 2, False), ("b", 2, None, True)], {"a": 2}),
                    (
                        "old_delete",
                        [("a", 3, 4, False), ("a", 2, None, True)],
                        {"a": 4},
                    ),
                ]
            ]
        ),
        ("nist-sms",),
        difficulty="medium",
        difficulty_reason="Retain deletion versions during reconciliation so old data cannot resurrect records.",
    )

    yield simple(
        "A27",
        "Late equipment dimension corrections overlap existing validity intervals",
        "effective_dimension_interval_rebuild",
        "changes contains effective/value records; last arrival wins for an equal effective time. "
        "Rebuild nonoverlapping validity intervals sorted by effective time: [start,next_start), final end=None. "
        "Return start/end/value records. Late arrivals split the preceding interval; adjacent equal values "
        "remain separate revisions.",
        """
        def run(request):
            versions = {r["effective"]: r["value"] for r in request["changes"]}
            times = sorted(versions)
            return [dict(start=t, end=times[i + 1] if i + 1 < len(times) else None, value=versions[t])
                    for i, t in enumerate(times)]
        """,
        ("times = sorted(versions)", "times = list(versions)"),
        {
            "inclusive_overlap": ("end=times[i + 1]", "end=times[i + 1] + 1"),
            "first_arrival_wins": (
                'for r in request["changes"]}',
                'for r in reversed(request["changes"])}',
            ),
        },
        examples(
            [
                (
                    n,
                    {"changes": [dict(effective=t, value=v) for t, v in rows]},
                    [dict(start=s, end=e, value=v) for s, e, v in expected],
                )
                for n, rows, expected in [
                    ("empty", [], []),
                    ("one", [(1, "a")], [(1, None, "a")]),
                    (
                        "late",
                        [(1, "a"), (5, "c"), (3, "b")],
                        [(1, 3, "a"), (3, 5, "b"), (5, None, "c")],
                    ),
                    ("ordered", [(1, "a"), (3, "b")], [(1, 3, "a"), (3, None, "b")]),
                    ("reverse", [(5, "c"), (1, "a")], [(1, 5, "a"), (5, None, "c")]),
                    ("correction", [(1, "a"), (1, "b")], [(1, None, "b")]),
                    ("same_value", [(1, "a"), (3, "a")], [(1, 3, "a"), (3, None, "a")]),
                    ("negative", [(0, "b"), (-2, "a")], [(-2, 0, "a"), (0, None, "b")]),
                    (
                        "middle_correction",
                        [(1, "a"), (3, "b"), (5, "c"), (3, "d")],
                        [(1, 3, "a"), (3, 5, "d"), (5, None, "c")],
                    ),
                    (
                        "late_before",
                        [(5, "b"), (2, "a")],
                        [(2, 5, "a"), (5, None, "b")],
                    ),
                ]
            ]
        ),
        ("nist-sms",),
        difficulty="medium",
        difficulty_reason="Rebuild temporal intervals after late arrivals and equal-time corrections.",
    )

    yield simple(
        "A28",
        "OEE performance uses one product's ideal cycle for every lot",
        "mixed_product_oee_composition",
        "planned>0 and 0<runtime<=planned are seconds. lots has total, good and ideal_cycle seconds per "
        "unit, with total>0, 0<=good<=total, ideal_cycle>0. Compute availability=runtime/planned, "
        "performance=sum(total*ideal_cycle)/runtime, quality=sum(good)/sum(total), and oee=their product. "
        "Do not clamp performance. Lots is nonempty. Test values are exactly representable.",
        """
        def run(request):
            lots = request["lots"]
            availability = request["runtime"] / request["planned"]
            ideal_time = sum(lot["total"] * lot["ideal_cycle"] for lot in lots)
            performance = ideal_time / request["runtime"]
            quality = sum(lot["good"] for lot in lots) / sum(lot["total"] for lot in lots)
            return dict(availability=availability, performance=performance, quality=quality, oee=availability * performance * quality)
        """,
        ('lot["total"] * lot["ideal_cycle"]', 'lot["total"] * lots[0]["ideal_cycle"]'),
        {
            "clamps_performance": (
                'ideal_time / request["runtime"]',
                'min(1, ideal_time / request["runtime"])',
            ),
            "uses_good_for_performance": (
                'lot["total"] * lot["ideal_cycle"]',
                'lot["good"] * lot["ideal_cycle"]',
            ),
        },
        examples(
            [
                (
                    n,
                    {
                        "planned": p,
                        "runtime": r,
                        "lots": [
                            dict(total=t, good=g, ideal_cycle=c) for t, g, c in lots
                        ],
                    },
                    dict(availability=a, performance=f, quality=q, oee=o),
                )
                for n, p, r, lots, a, f, q, o in [
                    ("perfect", 8, 8, [(4, 4, 2)], 1.0, 1.0, 1.0, 1.0),
                    ("downtime", 16, 8, [(4, 4, 2)], 0.5, 1.0, 1.0, 0.5),
                    ("mixed", 16, 8, [(2, 2, 1), (2, 2, 3)], 0.5, 1.0, 1.0, 0.5),
                    ("quality", 8, 8, [(4, 2, 2)], 1.0, 1.0, 0.5, 0.5),
                    (
                        "reverse_mixed",
                        16,
                        8,
                        [(2, 2, 3), (2, 2, 1)],
                        0.5,
                        1.0,
                        1.0,
                        0.5,
                    ),
                    ("above_one", 8, 4, [(4, 4, 2)], 0.5, 2.0, 1.0, 1.0),
                    ("zero_good", 8, 8, [(4, 0, 2)], 1.0, 1.0, 0.0, 0.0),
                    (
                        "all_factors",
                        16,
                        8,
                        [(2, 1, 1), (2, 1, 1)],
                        0.5,
                        0.5,
                        0.5,
                        0.125,
                    ),
                    (
                        "weighted_cycles",
                        16,
                        8,
                        [(1, 1, 1), (3, 1, 5)],
                        0.5,
                        2.0,
                        0.5,
                        0.5,
                    ),
                    ("fractional_cycle", 8, 4, [(4, 2, 0.5)], 0.5, 0.5, 0.5, 0.125),
                ]
            ]
        ),
        ("nist-sms",),
        difficulty="medium",
        difficulty_reason="Compose three distinct denominators while weighting mixed-product ideal cycle times.",
    )
