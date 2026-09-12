"""Manufacturing telemetry and production analytics repairs."""

from .easy import examples
from .schema import simple


def tasks():
    yield simple(
        "A11",
        "Irregular power sampling distorts integrated energy",
        "trapezoid_energy_integration",
        "samples is an unordered list of [second,watt] with unique integer seconds. Integrate the piecewise "
        "linear signal between the earliest and latest sample using trapezoids. Return joules; fewer than "
        "two samples return zero. Values are finite and nonnegative; do not extrapolate.",
        """
        def run(request):
            samples = sorted(request["samples"])
            return sum((b[0] - a[0]) * (a[1] + b[1]) / 2 for a, b in zip(samples, samples[1:]))
        """,
        ("(b[0] - a[0]) * (a[1] + b[1]) / 2", "(b[0] - a[0]) * a[1]"),
        {
            "unit_spacing": ("(b[0] - a[0]) * ", ""),
            "input_order": ('sorted(request["samples"])', 'request["samples"]'),
        },
        examples(
            [
                (n, {"samples": s}, v)
                for n, s, v in [
                    ("empty", [], 0),
                    ("single", [[0, 4]], 0),
                    ("ramp", [[0, 0], [2, 4]], 4),
                    ("flat", [[0, 3], [4, 3]], 12),
                    ("triangle", [[0, 0], [2, 4], [4, 0]], 8),
                    ("irregular", [[0, 0], [1, 4], [4, 4]], 14),
                    ("unordered", [[4, 0], [0, 0], [2, 4]], 8),
                    ("decline", [[0, 8], [2, 0]], 8),
                    ("offset", [[10, 2], [13, 4]], 9),
                    ("all_zero", [[0, 0], [7, 0]], 0),
                ]
            ]
        ),
        ("zema-hydraulic",),
        difficulty="medium",
        difficulty_reason="Account for elapsed time, interpolation and sample ordering together.",
    )

    yield simple(
        "A12",
        "Station joins discard parts with unavailable measurements",
        "part_measurement_left_join",
        "parts is an ordered unique list of part ids. measurements contains part/station/value records "
        "with unique part/station pairs. Return each part with a values list in requested station order. "
        "Missing values are None; retain numeric zero. Ignore records for unrequested parts or stations.",
        """
        def run(request):
            index = {(r["part"], r["station"]): r["value"] for r in request["measurements"]}
            return [dict(part=part, values=[index.get((part, station)) for station in request["stations"]])
                    for part in request["parts"]]
        """,
        ("index.get((part, station))", "index.get((part, station)) or None"),
        {
            "drops_missing_parts": (
                'for part in request["parts"]]',
                'for part in request["parts"] if any(p == part for p, _ in index)]',
            ),
            "station_collision": (
                '(r["part"], r["station"])',
                '(r["part"], request["stations"][0])',
            ),
        },
        examples(
            [
                (
                    n,
                    {
                        "parts": parts,
                        "stations": stations,
                        "measurements": [
                            dict(part=p, station=s, value=x) for p, s, x in rows
                        ],
                    },
                    [dict(part=p, values=x) for p, x in expected],
                )
                for n, parts, stations, rows, expected in [
                    ("empty", [], ["s"], [], []),
                    ("one", ["p"], ["s"], [("p", "s", 2)], [("p", [2])]),
                    ("zero", ["p"], ["s"], [("p", "s", 0)], [("p", [0])]),
                    ("missing", ["p"], ["s"], [], [("p", [None])]),
                    (
                        "stations",
                        ["p"],
                        ["a", "b"],
                        [("p", "a", 0), ("p", "b", 2)],
                        [("p", [0, 2])],
                    ),
                    (
                        "part_order",
                        ["q", "p"],
                        ["s"],
                        [("p", "s", 0)],
                        [("q", [None]), ("p", [0])],
                    ),
                    (
                        "station_order",
                        ["p"],
                        ["b", "a"],
                        [("p", "a", 1), ("p", "b", 2)],
                        [("p", [2, 1])],
                    ),
                    ("null", ["p"], ["s"], [("p", "s", None)], [("p", [None])]),
                    ("ignore", ["p"], ["s"], [("q", "s", 4)], [("p", [None])]),
                    ("no_stations", ["p"], [], [], [("p", [])]),
                ]
            ]
        ),
        ("bosch", "secom"),
        difficulty="medium",
        difficulty_reason="Preserve join cardinality, identity, order and missing-value semantics.",
    )

    yield simple(
        "A13",
        "Machine counter resets subtract completed production",
        "reset_aware_counter_delta",
        "samples contains [sequence,count] readings with unique positive sequence and nonnegative count. "
        "Sort by sequence. The first reading is the baseline, contributing zero. Subsequent increases "
        "contribute the difference; a decrease denotes reset to zero and contributes the new count. Return total.",
        """
        def run(request):
            samples = sorted(request["samples"])
            return sum(b[1] - a[1] if b[1] >= a[1] else b[1] for a, b in zip(samples, samples[1:]))
        """,
        ("b[1] - a[1] if b[1] >= a[1] else b[1]", "b[1] - a[1]"),
        {
            "drops_reset_production": ("else b[1]", "else 0"),
            "counts_baseline": (
                "return sum(",
                "return (samples[0][1] if samples else 0) + sum(",
            ),
        },
        examples(
            [
                (n, {"samples": s}, v)
                for n, s, v in [
                    ("empty", [], 0),
                    ("single", [[1, 8]], 0),
                    ("reset", [[1, 9], [2, 2]], 2),
                    ("increase", [[1, 2], [2, 5]], 3),
                    ("multiple", [[1, 8], [2, 1], [3, 3], [4, 2]], 5),
                    ("unordered", [[3, 3], [1, 8], [2, 1]], 3),
                    ("zero_reset", [[1, 9], [2, 0], [3, 2]], 2),
                    ("equal", [[1, 4], [2, 4]], 0),
                    ("initial_zero", [[1, 0], [2, 7]], 7),
                    ("reset_then_increase", [[1, 100], [2, 4], [3, 9]], 9),
                ]
            ]
        ),
        ("nist-sms",),
        difficulty="medium",
        difficulty_reason="Distinguish counter reset from negative production using ordered observations.",
    )

    yield simple(
        "A14",
        "Backfilled calibration is applied before its effective time",
        "event_time_calibration_asof",
        "calibrations contains unique effective times with gain and offset. For each sample [time,value], "
        "use the calibration with greatest effective<=time, regardless of input order. Return value*gain+offset "
        "or None when no calibration exists. Preserve sample order.",
        """
        def run(request):
            rows = sorted(request["calibrations"], key=lambda r: r["effective"])
            output = []
            for time, value in request["samples"]:
                eligible = [r for r in rows if r["effective"] <= time]
                rule = eligible[-1] if eligible else None
                output.append(value * rule["gain"] + rule["offset"] if rule else None)
            return output
        """,
        ('r["effective"] <= time', 'r["effective"] >= time'),
        {
            "first_rule": ("eligible[-1]", "eligible[0]"),
            "ignores_offset": (' + rule["offset"]', ""),
        },
        examples(
            [
                (
                    n,
                    {
                        "calibrations": [
                            dict(effective=t, gain=g, offset=o) for t, g, o in c
                        ],
                        "samples": s,
                    },
                    v,
                )
                for n, c, s, v in [
                    ("empty", [], [], []),
                    ("exact", [(2, 2, 1)], [[2, 3]], [7]),
                    ("after", [(2, 2, 1)], [[3, 3]], [7]),
                    ("no_rules", [], [[1, 3]], [None]),
                    ("before", [(2, 2, 1)], [[1, 3]], [None]),
                    ("latest", [(0, 1, 0), (2, 2, 1)], [[3, 3]], [7]),
                    ("unsorted", [(2, 2, 1), (0, 1, 0)], [[1, 3], [3, 3]], [3, 7]),
                    ("boundary", [(0, 1, 0), (2, 2, 1)], [[2, 3]], [7]),
                    ("zero_gain", [(0, 0, 5)], [[1, 9]], [5]),
                    ("sample_order", [(0, 1, 0), (2, 2, 1)], [[3, 2], [1, 2]], [5, 2]),
                ]
            ]
        ),
        ("zema-hydraulic",),
        difficulty="medium",
        difficulty_reason="Perform an ordered temporal join without future-data leakage.",
    )

    yield simple(
        "A15",
        "Late production events fail to bridge adjacent activity sessions",
        "late_event_session_merge",
        "times contains integer event times, potentially unordered and duplicated. Sort and deduplicate. "
        "Consecutive times belong to the same session when their gap<=gap; sessions return [first,last,count]. "
        "gap is nonnegative. A late event can connect two formerly separate sessions.",
        """
        def run(request):
            sessions = []
            for time in sorted(set(request["times"])):
                if sessions and time - sessions[-1][1] <= request["gap"]:
                    sessions[-1][1] = time
                    sessions[-1][2] += 1
                else:
                    sessions.append([time, time, 1])
            return sessions
        """,
        ('sorted(set(request["times"]))', 'list(dict.fromkeys(request["times"]))'),
        {
            "strict_gap": ('<= request["gap"]', '< request["gap"]'),
            "counts_duplicates": (
                'sorted(set(request["times"]))',
                'sorted(request["times"])',
            ),
        },
        examples(
            [
                (n, {"gap": g, "times": t}, v)
                for n, g, t, v in [
                    ("empty", 2, [], []),
                    ("one", 2, [3], [[3, 3, 1]]),
                    ("late_bridge", 3, [0, 6, 3], [[0, 6, 3]]),
                    ("separate", 2, [0, 5], [[0, 0, 1], [5, 5, 1]]),
                    ("reverse", 2, [4, 2, 0], [[0, 4, 3]]),
                    ("exact_gap", 2, [0, 2], [[0, 2, 2]]),
                    ("duplicates", 2, [0, 0, 2], [[0, 2, 2]]),
                    ("zero_gap", 0, [1, 1, 2], [[1, 1, 1], [2, 2, 1]]),
                    ("two_sessions", 2, [9, 1, 0, 8], [[0, 1, 2], [8, 9, 2]]),
                    ("negative", 2, [0, -2, -4], [[-4, 0, 3]]),
                ]
            ]
        ),
        ("production-log",),
        difficulty="medium",
        difficulty_reason="Reconstruct sessions after late arrivals and duplicate suppression.",
    )

    yield simple(
        "A16",
        "Control limits include the measurements being evaluated",
        "frozen_control_chart_baseline",
        "baseline has at least two finite numbers. Compute its mean and sample standard deviation (n-1). "
        "Return booleans for measurements strictly outside mean +/- k*stdev; equality is in control. "
        "k>=0. Evaluation measurements must not change baseline statistics.",
        """
        import statistics
        def run(request):
            baseline = request["baseline"]
            center = statistics.mean(baseline)
            width = request["k"] * statistics.stdev(baseline)
            return [abs(value - center) > width for value in request["measurements"]]
        """,
        (
            'baseline = request["baseline"]',
            'baseline = request["baseline"] + request["measurements"]',
        ),
        {
            "population_variance": ("statistics.stdev", "statistics.pstdev"),
            "inclusive_limit": ("> width", ">= width"),
        },
        examples(
            [
                (n, {"baseline": b, "k": k, "measurements": m}, v)
                for n, b, k, m, v in [
                    ("empty", [0, 2], 1, [], []),
                    ("center", [0, 2], 1, [1], [False]),
                    ("spike", [0, 2], 2, [100], [True]),
                    ("flat", [1, 1], 2, [1], [False]),
                    ("lower_spike", [0, 2], 2, [-100], [True]),
                    ("sample_denominator", [0, 2], 1, [2.25], [False]),
                    ("zero_width", [1, 1], 1, [1, 2], [False, True]),
                    ("zero_multiplier", [0, 2], 0, [1, 2], [False, True]),
                    ("opposite_outliers", [0, 2], 2, [-100, 100], [True, True]),
                    ("constant_baseline", [4, 4, 4], 1, [3, 4, 5], [True, False, True]),
                ]
            ]
        ),
        ("zema-hydraulic",),
        difficulty="medium",
        difficulty_reason="Keep calibration and evaluation populations separate and choose the correct variance estimator.",
    )

    yield simple(
        "A17",
        "Rotated inspection coordinates apply translation in the wrong frame",
        "inspection_rigid_transform",
        "points is a list of [x,y]. Rotate counterclockwise by turns quarter turns about the origin, then "
        "translate by [dx,dy]. turns is any integer, including negative. Return transformed points in order.",
        """
        def run(request):
            output = []
            for x, y in request["points"]:
                for _ in range(request["turns"] % 4):
                    x, y = -y, x
                output.append([x + request["dx"], y + request["dy"]])
            return output
        """,
        ("x, y = -y, x", "x, y = y, -x"),
        {
            "drops_translation": ('[x + request["dx"], y + request["dy"]]', "[x, y]"),
            "clamps_rotation": ('request["turns"] % 4', 'max(0, request["turns"])'),
        },
        examples(
            [
                (n, {"points": p, "turns": t, "dx": dx, "dy": dy}, v)
                for n, p, t, dx, dy, v in [
                    ("empty", [], 1, 0, 0, []),
                    ("identity", [[1, 2]], 0, 0, 0, [[1, 2]]),
                    ("quarter", [[1, 2]], 1, 0, 0, [[-2, 1]]),
                    ("half", [[1, 2]], 2, 0, 0, [[-1, -2]]),
                    ("translate_after", [[1, 2]], 1, 4, 5, [[2, 6]]),
                    ("negative", [[1, 2]], -1, 0, 0, [[2, -1]]),
                    ("three", [[1, 2]], 3, 0, 0, [[2, -1]]),
                    ("wrap", [[1, 2]], 5, 0, 0, [[-2, 1]]),
                    ("origin", [[0, 0]], 3, -1, 2, [[-1, 2]]),
                    ("many", [[1, 0], [0, 1]], 1, 1, 1, [[1, 2], [0, 1]]),
                ]
            ]
        ),
        ("nist-sms",),
        difficulty="medium",
        difficulty_reason="Preserve orientation and coordinate-frame operation order.",
    )

    yield simple(
        "A18",
        "Multirate sensor alignment accepts readings outside tolerance",
        "nearest_sensor_alignment",
        "readings contains unique [time,value] pairs. For each query time choose the nearest reading within "
        "inclusive tolerance, breaking distance ties toward earlier time. Return value or None. Inputs may "
        "be unordered; queries retain their order. tolerance>=0.",
        """
        def run(request):
            output = []
            for time in request["queries"]:
                candidates = [r for r in request["readings"] if abs(r[0] - time) <= request["tolerance"]]
                nearest = min(candidates, key=lambda r: (abs(r[0] - time), r[0])) if candidates else None
                output.append(nearest[1] if nearest else None)
            return output
        """,
        (
            'abs(r[0] - time) <= request["tolerance"]',
            'r[0] - time <= request["tolerance"]',
        ),
        {
            "late_tie": ("(abs(r[0] - time), r[0])", "(abs(r[0] - time), -r[0])"),
            "strict_tolerance": ('<= request["tolerance"]', '< request["tolerance"]'),
        },
        examples(
            [
                (n, {"readings": r, "queries": q, "tolerance": t}, v)
                for n, r, q, t, v in [
                    ("empty", [], [1], 2, [None]),
                    ("exact", [[1, 4]], [1], 0, [4]),
                    ("stale", [[0, 4]], [10], 2, [None]),
                    ("future_far", [[10, 4]], [0], 2, [None]),
                    ("inclusive", [[0, 4]], [2], 2, [4]),
                    ("tie", [[4, 8], [0, 2]], [2], 2, [2]),
                    ("zero_value", [[0, 0]], [0], 0, [0]),
                    ("ordered_output", [[0, 2], [4, 8]], [4, 0], 0, [8, 2]),
                    ("negative", [[-4, 2]], [0], 1, [None]),
                    ("nearest", [[0, 2], [3, 6], [9, 18]], [2], 2, [6]),
                ]
            ]
        ),
        ("zema-hydraulic",),
        difficulty="medium",
        difficulty_reason="Join signals by absolute distance with explicit tolerance and tie behavior.",
    )

    yield simple(
        "A19",
        "Repeated leaf records inflate hierarchical yield reports",
        "leaf_identity_yield_rollup",
        "rows contains group/part/good records. The last row for a part is its authoritative group and "
        "boolean good status. Return sorted groups mapping to {good,total}, counting each unique part once. "
        "Groups with no current members are omitted; part identity is global.",
        """
        def run(request):
            current = {r["part"]: r for r in request["rows"]}
            groups = {}
            for row in current.values():
                counts = groups.setdefault(row["group"], dict(good=0, total=0))
                counts["total"] += 1
                counts["good"] += int(row["good"])
            return dict(sorted(groups.items()))
        """,
        (
            '{r["part"]: r for r in request["rows"]}',
            '{i: r for i, r in enumerate(request["rows"])}',
        ),
        {
            "first_record_wins": (
                'for r in request["rows"]}',
                'for r in reversed(request["rows"])}',
            ),
            "group_local_identity": ('r["part"]: r', '(r["group"], r["part"]): r'),
        },
        examples(
            [
                (
                    n,
                    {"rows": [dict(group=g, part=p, good=b) for g, p, b in rows]},
                    {g: dict(good=a, total=b) for g, (a, b) in v.items()},
                )
                for n, rows, v in [
                    ("empty", [], {}),
                    ("one", [("g", "p", True)], {"g": (1, 1)}),
                    ("repeat", [("g", "p", True), ("g", "p", True)], {"g": (1, 1)}),
                    ("two", [("g", "p", True), ("g", "q", False)], {"g": (1, 2)}),
                    (
                        "correction",
                        [("g", "p", False), ("g", "p", True)],
                        {"g": (1, 1)},
                    ),
                    ("move", [("g", "p", True), ("h", "p", False)], {"h": (0, 1)}),
                    (
                        "move_back",
                        [("g", "p", True), ("h", "p", False), ("g", "p", True)],
                        {"g": (1, 1)},
                    ),
                    (
                        "groups",
                        [("g", "p", True), ("h", "q", False)],
                        {"g": (1, 1), "h": (0, 1)},
                    ),
                    ("downgrade", [("g", "p", True), ("g", "p", False)], {"g": (0, 1)}),
                    (
                        "shared_group",
                        [("g", "p", True), ("g", "q", True), ("h", "p", False)],
                        {"g": (1, 1), "h": (0, 1)},
                    ),
                ]
            ]
        ),
        ("production-log", "secom"),
        difficulty="medium",
        difficulty_reason="Resolve record identity and corrections before aggregation across changing groups.",
    )
