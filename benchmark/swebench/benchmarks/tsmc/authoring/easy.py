"""Eighteen distinct boundary, identity and aggregation repair problems."""

from .schema import Case, simple


def examples(rows):
    return [
        Case(name, request, expected, public=index < 4)
        for index, (name, request, expected) in enumerate(rows)
    ]


def tasks():
    yield simple(
        "F05",
        "Expired material remains available at its expiry boundary",
        "material_expiry",
        "A material is usable strictly before its expires_at minute. Return one boolean per lot. "
        "now and expires_at are integer UTC minutes; zero and negative historical timestamps are valid.",
        """
        def run(request):
            now = request["now"]
            return [now < lot["expires_at"] for lot in request["lots"]]
        """,
        ("now < lot", "now <= lot"),
        {
            "expires_early": ("now < lot", "now + 1 < lot"),
            "rejects_fresh": ('return [now < lot["expires_at"]', "return [False"),
        },
        examples(
            [
                (
                    name,
                    {
                        "now": now,
                        "lots": [{"expires_at": expiry} for expiry in expires],
                    },
                    expected,
                )
                for name, now, expires, expected in [
                    ("fresh", 10, [11], [True]),
                    ("expired", 10, [9], [False]),
                    ("boundary", 10, [10], [False]),
                    ("empty", 10, [], []),
                    ("zero_boundary", 0, [0], [False]),
                    ("historical", -3, [-4, -3, -2], [False, False, True]),
                    ("mixed", 20, [19, 20, 21, 40], [False, False, True, True]),
                    ("large_epoch", 1000000, [1000000, 1000001], [False, True]),
                    ("duplicates", 4, [4, 4, 5], [False, False, True]),
                    ("far_future", 0, [100], [True]),
                ]
            ]
        ),
        ("production-log",),
    )

    yield simple(
        "F06",
        "Recipe revisions sort lexically instead of numerically",
        "numeric_recipe_revision",
        "Select the numerically greatest dotted revision string. All revisions have three nonnegative "
        "integer components without leading zeros. Empty input returns None. Preserve the original string.",
        """
        def run(request):
            versions = request["versions"]
            return max(versions, key=lambda v: tuple(map(int, v.split(".")))) if versions else None
        """,
        ('tuple(map(int, v.split(".")))', 'tuple(v.split("."))'),
        {
            "major_only": ('tuple(map(int, v.split(".")))', 'int(v.split(".")[0])'),
            "reversed_components": (
                'tuple(map(int, v.split(".")))',
                'tuple(reversed(tuple(map(int, v.split(".")))))',
            ),
        },
        examples(
            [
                (name, {"versions": values}, expected)
                for name, values, expected in [
                    ("empty", [], None),
                    ("single", ["1.0.0"], "1.0.0"),
                    ("major_numeric", ["2.0.0", "10.0.0"], "10.0.0"),
                    ("normal", ["1.0.0", "2.0.0"], "2.0.0"),
                    ("minor_numeric", ["1.9.0", "1.12.0"], "1.12.0"),
                    ("patch_numeric", ["1.1.9", "1.1.11"], "1.1.11"),
                    ("major_priority", ["2.0.0", "1.99.99"], "2.0.0"),
                    ("patch_tie_break", ["1.2.1", "1.2.2"], "1.2.2"),
                    ("duplicate", ["1.0.0", "1.0.0"], "1.0.0"),
                    ("zero", ["0.0.0", "0.0.12", "0.0.9"], "0.0.12"),
                ]
            ]
        ),
        ("nist-sms",),
    )

    yield simple(
        "F07",
        "Repeated route steps send lots back to the wrong occurrence",
        "route_occurrence_cursor",
        "route is an ordered list of step names, with repeats allowed. completed is the number of completed "
        "occurrences, between zero and len(route). Return the next step or None when complete.",
        """
        def run(request):
            route = request["route"]
            position = request["completed"]
            return route[position] if position < len(route) else None
        """,
        (
            'position = request["completed"]',
            'position = (route.index(route[request["completed"] - 1]) + 1) if request["completed"] else 0',
        ),
        {
            "skips_step": (
                'position = request["completed"]',
                'position = request["completed"] + 1',
            ),
            "repeats_previous": (
                'position = request["completed"]',
                'position = max(0, request["completed"] - 1)',
            ),
        },
        examples(
            [
                (name, {"route": route, "completed": count}, expected)
                for name, route, count, expected in [
                    ("start", ["wash", "coat"], 0, "wash"),
                    ("advance", ["wash", "coat"], 1, "coat"),
                    (
                        "rework_occurrence",
                        ["wash", "coat", "wash", "inspect"],
                        3,
                        "inspect",
                    ),
                    ("empty", [], 0, None),
                    ("repeat_at_end", ["a", "b", "a"], 3, None),
                    ("triple_repeat", ["a", "a", "a", "b"], 3, "b"),
                    ("done", ["a", "b"], 2, None),
                    ("same_names", ["a", "a"], 2, None),
                    ("middle", ["a", "b", "c"], 2, "c"),
                    ("later_repeat", ["a", "b", "c", "b", "d"], 4, "d"),
                ]
            ]
        ),
        ("production-log",),
    )

    yield simple(
        "F08",
        "Overnight staffing windows disappear after midnight",
        "overnight_shift_membership",
        "For each integer minute in [0,1440), return whether it belongs to [start,end). If start>end the "
        "shift crosses midnight. Equal endpoints describe an empty shift. No timezone conversion is requested.",
        """
        def run(request):
            start, end = request["start"], request["end"]
            return [(start <= t < end if start <= end else t >= start or t < end)
                    for t in request["minutes"]]
        """,
        ("else t >= start or t < end", "else t >= start and t < end"),
        {
            "includes_end": (
                "else t >= start or t < end",
                "else t >= start or t <= end",
            ),
            "misses_evening": ("else t >= start or t < end", "else t < end"),
        },
        examples(
            [
                (name, {"start": start, "end": end, "minutes": values}, expected)
                for name, start, end, values, expected in [
                    ("day", 480, 960, [479, 480, 959, 960], [False, True, True, False]),
                    (
                        "night",
                        1320,
                        360,
                        [0, 359, 360, 1319, 1320],
                        [True, True, False, False, True],
                    ),
                    ("empty", 0, 0, [0, 1], [False, False]),
                    ("no_queries", 10, 20, [], []),
                    ("midnight_start", 0, 60, [0, 59, 60], [True, True, False]),
                    (
                        "midnight_end",
                        1380,
                        0,
                        [0, 1379, 1380, 1439],
                        [False, False, True, True],
                    ),
                    ("short_wrap", 1439, 1, [1439, 0, 1], [True, True, False]),
                    ("equal_nonzero", 20, 20, [19, 20, 21], [False, False, False]),
                    ("single_minute", 4, 5, [3, 4, 5], [False, True, False]),
                    ("wrap_middle", 1200, 300, [1201, 200, 400], [True, True, False]),
                ]
            ]
        ),
        ("production-log",),
    )

    yield simple(
        "F09",
        "Partial carrier loads are omitted from packaging counts",
        "carrier_ceiling_division",
        "Return the minimum whole carriers needed for quantity units with positive integer capacity. "
        "quantity is a nonnegative integer; an empty order needs zero carriers.",
        """
        def run(request):
            quantity, capacity = request["quantity"], request["capacity"]
            return (quantity + capacity - 1) // capacity
        """,
        ("(quantity + capacity - 1) // capacity", "quantity // capacity"),
        {
            "extra_full_carrier": (
                "(quantity + capacity - 1) // capacity",
                "quantity // capacity + 1",
            ),
            "empty_carrier": (
                "return (quantity + capacity - 1) // capacity",
                "return max(1, (quantity + capacity - 1) // capacity)",
            ),
        },
        examples(
            [
                (f"quantity_{q}_capacity_{c}", {"quantity": q, "capacity": c}, expected)
                for q, c, expected in [
                    (0, 25, 0),
                    (25, 25, 1),
                    (26, 25, 2),
                    (50, 25, 2),
                    (1, 25, 1),
                    (49, 25, 2),
                    (51, 25, 3),
                    (1000001, 1000, 1001),
                    (7, 1, 7),
                    (0, 1, 0),
                ]
            ]
        ),
        ("production-log",),
    )

    yield simple(
        "F10",
        "Missing interlock observations are treated as safe",
        "missing_interlock_observation",
        "Return True only if every required interlock name is present with JSON boolean true. Missing, "
        "false and nonboolean observations are unsafe. An empty required list is satisfied.",
        """
        def run(request):
            observations = request["observations"]
            return all(observations.get(name, False) is True for name in request["required"])
        """,
        ("get(name, False)", "get(name, True)"),
        {
            "any_interlock": ("return all(", "return any("),
            "truthy_interlock": (
                "observations.get(name, False) is True",
                "bool(observations.get(name, False))",
            ),
        },
        examples(
            [
                (name, {"required": required, "observations": values}, expected)
                for name, required, values, expected in [
                    ("safe", ["door"], {"door": True}, True),
                    ("unsafe", ["door"], {"door": False}, False),
                    ("missing", ["door"], {}, False),
                    ("empty", [], {}, True),
                    ("partial", ["door", "vacuum"], {"door": True}, False),
                    (
                        "one_unsafe",
                        ["door", "vacuum"],
                        {"door": True, "vacuum": False},
                        False,
                    ),
                    ("numeric_true", ["door"], {"door": 1}, False),
                    ("text_true", ["door"], {"door": "true"}, False),
                    ("unrelated", ["door"], {"vacuum": True}, False),
                    (
                        "all_safe",
                        ["door", "vacuum"],
                        {"door": True, "vacuum": True},
                        True,
                    ),
                ]
            ]
        ),
        ("nist-sms",),
    )

    yield simple(
        "A05",
        "Yield aggregation gives small lots the same weight as large lots",
        "weighted_yield_denominator",
        "Each lot has integer good and tested counts with 0<=good<=tested and tested>0. Return total good / "
        "total tested across lots, or None for an empty list. Output comparisons use exactly representable examples.",
        """
        def run(request):
            lots = request["lots"]
            return sum(lot["good"] for lot in lots) / sum(lot["tested"] for lot in lots) if lots else None
        """,
        (
            'sum(lot["good"] for lot in lots) / sum(lot["tested"] for lot in lots)',
            'sum(lot["good"] / lot["tested"] for lot in lots) / len(lots)',
        ),
        {
            "last_lot": (
                'sum(lot["good"] for lot in lots) / sum(lot["tested"] for lot in lots)',
                'lots[-1]["good"] / lots[-1]["tested"]',
            ),
            "counts_lots": ('sum(lot["tested"] for lot in lots)', "len(lots)"),
        },
        examples(
            [
                (name, {"lots": [{"good": g, "tested": n} for g, n in lots]}, expected)
                for name, lots, expected in [
                    ("empty", [], None),
                    ("single", [(1, 2)], 0.5),
                    ("unequal", [(1, 1), (0, 3)], 0.25),
                    ("equal_sizes", [(2, 2), (0, 2)], 0.5),
                    ("large_bad_lot", [(1, 1), (0, 7)], 0.125),
                    ("reversed", [(0, 3), (1, 1)], 0.25),
                    ("all_good", [(2, 2), (6, 6)], 1.0),
                    ("all_bad", [(0, 2), (0, 6)], 0.0),
                    ("three_lots", [(2, 2), (1, 2), (1, 4)], 0.5),
                    ("duplicate_lots", [(1, 1), (0, 3), (1, 1), (0, 3)], 0.25),
                ]
            ]
        ),
        ("secom",),
    )

    yield simple(
        "A06",
        "Nearest-rank quantiles select the following observation",
        "nearest_rank_quantile",
        "Return the nearest-rank quantile of finite numeric values: sort ascending, select one-based rank "
        "max(1,ceil(q*n)), for q in [0,1]. Empty input returns None. Preserve duplicates.",
        """
        import math
        def run(request):
            values = sorted(request["values"])
            index = max(0, math.ceil(request["q"] * len(values)) - 1)
            return values[index] if values else None
        """,
        (
            'max(0, math.ceil(request["q"] * len(values)) - 1)',
            'min(len(values) - 1, int(request["q"] * len(values)))',
        ),
        {
            "interpolation_rank": (
                'max(0, math.ceil(request["q"] * len(values)) - 1)',
                'int(request["q"] * max(0, len(values) - 1))',
            ),
            "descending": (
                'sorted(request["values"])',
                'sorted(request["values"], reverse=True)',
            ),
        },
        examples(
            [
                (name, {"values": v, "q": q}, expected)
                for name, v, q, expected in [
                    ("empty", [], 0.5, None),
                    ("single", [5], 0.8, 5),
                    ("even_median", [4, 1, 3, 2], 0.5, 2),
                    ("minimum", [2, 1], 0, 1),
                    ("maximum", [2, 1], 1, 2),
                    ("upper_quartile", [1, 2, 3, 4], 0.75, 3),
                    ("odd_median", [3, 1, 2], 0.5, 2),
                    ("noninteger_rank", [1, 2, 3, 4], 0.6, 3),
                    ("duplicates", [1, 1, 1, 9], 0.75, 1),
                    ("negative", [-1, -4, -2, -3], 0.5, -3),
                ]
            ]
        ),
        ("zema-hydraulic",),
    )

    yield simple(
        "A07",
        "Unavailable measurements bias the sensor mean toward zero",
        "missing_measurement_mean",
        "values contains finite numbers or None for unavailable measurements. Average only numeric "
        "measurements, including zero and negative values; return None if none are available.",
        """
        def run(request):
            values = [v for v in request["values"] if v is not None]
            return sum(values) / len(values) if values else None
        """,
        (
            '[v for v in request["values"] if v is not None]',
            '[0 if v is None else v for v in request["values"]]',
        ),
        {
            "drops_zero": ("if v is not None]", "if v is not None and v != 0]"),
            "drops_negative": ("if v is not None]", "if v is not None and v >= 0]"),
        },
        examples(
            [
                (name, {"values": v}, expected)
                for name, v, expected in [
                    ("empty", [], None),
                    ("available", [1, 3], 2.0),
                    ("missing", [2, None], 2.0),
                    ("zero", [0, 4], 2.0),
                    ("all_missing", [None, None], None),
                    ("negative", [-4, 2], -1.0),
                    ("mixed", [None, -2, 0, 2], 0.0),
                    ("repeated_missing", [None, 8, None], 8.0),
                    ("single_zero", [0], 0.0),
                    ("four_values", [2, 4, 6, 8, None], 5.0),
                ]
            ]
        ),
        ("secom",),
    )

    yield simple(
        "A08",
        "The maximum in-range measurement is lost from histograms",
        "closed_final_histogram_bin",
        "edges is a strictly increasing numeric list of at least two entries. All bins are [left,right), "
        "except the final bin includes the final edge. Ignore values outside the edges; return bin counts.",
        """
        from bisect import bisect_right
        def run(request):
            edges = request["edges"]
            counts = [0] * (len(edges) - 1)
            for value in request["values"]:
                index = bisect_right(edges, value) - 1
                if value == edges[-1]:
                    index -= 1
                if 0 <= index < len(counts):
                    counts[index] += 1
            return counts
        """,
        ("if value == edges[-1]:", "if False:"),
        {
            "excludes_first": (
                "if 0 <= index < len(counts):",
                "if 0 <= index < len(counts) and value != edges[0]:",
            ),
            "wrong_internal_edge": (
                "bisect_right(edges, value)",
                "bisect_right(edges, value - 0.0001)",
            ),
        },
        examples(
            [
                (name, {"edges": edges, "values": values}, expected)
                for name, edges, values, expected in [
                    ("interior", [0, 10, 20], [5, 15], [1, 1]),
                    ("last_edge", [0, 10, 20], [20], [0, 1]),
                    ("outside", [0, 10], [-1, 11], [0]),
                    ("empty", [0, 10], [], [0]),
                    ("all_edges", [0, 10, 20], [0, 10, 20], [1, 2]),
                    ("single_bin", [0, 1], [0, 0.5, 1], [3]),
                    ("negative", [-3, -1, 2], [-3, -1, 2], [1, 2]),
                    ("repeated_max", [0, 5], [5, 5, 5], [3]),
                    ("uneven_bins", [0, 1, 100], [0.5, 1, 99, 100], [1, 3]),
                    ("boundary_pair", [2, 4], [2, 4], [2]),
                ]
            ]
        ),
        ("zema-hydraulic",),
    )

    yield simple(
        "A09",
        "Alarm hysteresis misses threshold equality",
        "hysteresis_transition_boundaries",
        "Process values in order. An inactive alarm activates at value>=high; an active alarm clears at "
        "value<=low. Between low and high preserve its state. low<high; return state after every sample.",
        """
        def run(request):
            active = request["initial"]
            states = []
            for value in request["values"]:
                if not active and value >= request["high"]:
                    active = True
                elif active and value <= request["low"]:
                    active = False
                states.append(active)
            return states
        """,
        ('value >= request["high"]', 'value > request["high"]'),
        {
            "late_clear": ('value <= request["low"]', 'value < request["low"]'),
            "clears_deadband": ('value <= request["low"]', 'value < request["high"]'),
        },
        examples(
            [
                (
                    name,
                    {"low": low, "high": high, "initial": initial, "values": values},
                    expected,
                )
                for name, low, high, initial, values, expected in [
                    ("quiet", 2, 5, False, [1, 3, 4], [False, False, False]),
                    ("equality", 2, 5, False, [5], [True]),
                    ("empty", 2, 5, False, [], []),
                    ("above", 2, 5, False, [6], [True]),
                    ("retains_deadband", 2, 5, False, [5, 3, 2], [True, True, False]),
                    ("clear_equality", 2, 5, True, [2], [False]),
                    ("reactivate", 2, 5, True, [1, 5], [False, True]),
                    ("negative", -5, -2, False, [-2, -4, -5], [True, True, False]),
                    ("chatter", 2, 5, False, [5, 4, 5, 3], [True, True, True, True]),
                    ("initial_active", 2, 5, True, [3, 4], [True, True]),
                ]
            ]
        ),
        ("zema-hydraulic",),
    )

    yield simple(
        "A10",
        "Rounding each measurement before aggregation changes totals",
        "decimal_aggregate_rounding",
        "values are decimal strings. Sum their exact decimal values, then round the total to two decimal "
        "places using ROUND_HALF_UP, returning a fixed two-place string. Empty input returns '0.00'.",
        """
        from decimal import Decimal, ROUND_HALF_UP
        def run(request):
            values = [Decimal(value) for value in request["values"]]
            total = sum(values, Decimal(0))
            return format(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), ".2f")
        """,
        (
            "sum(values, Decimal(0))",
            'sum((v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) for v in values), Decimal(0))',
        ),
        {
            "bankers_rounding": (
                "rounding=ROUND_HALF_UP",
                'rounding="ROUND_HALF_EVEN"',
            ),
            "truncation": ("rounding=ROUND_HALF_UP", 'rounding="ROUND_DOWN"'),
        },
        examples(
            [
                (name, {"values": values}, expected)
                for name, values, expected in [
                    ("empty", [], "0.00"),
                    ("whole", ["2", "3"], "5.00"),
                    ("sum_before_round", ["0.004", "0.004"], "0.01"),
                    ("single_tie", ["1.005"], "1.01"),
                    ("negative_tie", ["-1.005"], "-1.01"),
                    ("offsetting", ["1.234", "-0.234"], "1.00"),
                    ("many_small", ["0.003"] * 4, "0.01"),
                    ("double_tie", ["0.005", "0.005"], "0.01"),
                    ("exact_cents", ["1.25", "2.75"], "4.00"),
                    ("negative_sum", ["-0.004", "-0.004"], "-0.01"),
                ]
            ]
        ),
        ("bpi-2019",),
    )

    yield simple(
        "R05",
        "Retries continue after one of their budgets is exhausted",
        "conjunctive_retry_budget",
        "attempts counts calls already made. Allow another attempt only when attempts<max_attempts AND "
        "elapsed<deadline. All four values are nonnegative finite numbers, and attempt counts are integers.",
        """
        def run(request):
            return request["attempts"] < request["max_attempts"] and request["elapsed"] < request["deadline"]
        """,
        (" and ", " or "),
        {
            "attempt_boundary": ('request["attempts"] <', 'request["attempts"] <='),
            "time_boundary": ('request["elapsed"] <', 'request["elapsed"] <='),
        },
        examples(
            [
                (
                    name,
                    {"attempts": a, "max_attempts": m, "elapsed": e, "deadline": d},
                    expected,
                )
                for name, a, m, e, d, expected in [
                    ("available", 0, 3, 0, 10, True),
                    ("all_exhausted", 3, 3, 10, 10, False),
                    ("attempts_exhausted", 3, 3, 0, 10, False),
                    ("time_exhausted", 0, 3, 10, 10, False),
                    ("zero_calls", 0, 0, 0, 10, False),
                    ("zero_time", 0, 3, 0, 0, False),
                    ("last_attempt", 2, 3, 9, 10, True),
                    ("over_attempts", 4, 3, 1, 10, False),
                    ("over_time", 1, 3, 11, 10, False),
                    ("fractional_time", 0, 1, 0.5, 1, True),
                ]
            ]
        ),
        ("nist-sms",),
    )

    yield simple(
        "R06",
        "Retry jitter exceeds the configured maximum delay",
        "post_jitter_backoff_cap",
        "Return min(cap, base*2**attempt+jitter). attempt is an integer in [0,20]; base>0, cap>=base, "
        "jitter>=0. Jitter is supplied explicitly so tests do not depend on random number generators.",
        """
        def run(request):
            base, cap = request["base"], request["cap"]
            return min(cap, base * 2 ** request["attempt"] + request["jitter"])
        """,
        (
            'min(cap, base * 2 ** request["attempt"] + request["jitter"])',
            'min(cap, base * 2 ** request["attempt"]) + request["jitter"]',
        ),
        {
            "linear_growth": ('2 ** request["attempt"]', '(request["attempt"] + 1)'),
            "drops_jitter": (' + request["jitter"]', ""),
        },
        examples(
            [
                (name, {"base": b, "cap": c, "attempt": a, "jitter": j}, expected)
                for name, b, c, a, j, expected in [
                    ("initial", 1, 10, 0, 0, 1),
                    ("second", 1, 10, 1, 1, 3),
                    ("capped", 1, 10, 4, 2, 10),
                    ("exact_cap", 1, 8, 3, 0, 8),
                    ("jitter_crosses_cap", 1, 10, 3, 5, 10),
                    ("exponential", 1, 100, 3, 0, 8),
                    ("fractional", 0.5, 5, 2, 0.5, 2.5),
                    ("minimum_cap", 2, 2, 0, 3, 2),
                    ("large_attempt", 1, 100, 20, 1, 100),
                    ("within_cap", 2, 30, 2, 3, 11),
                ]
            ]
        ),
        ("nist-sms",),
    )

    yield simple(
        "R07",
        "Cache entries remain readable at their TTL boundary",
        "cache_ttl_boundary",
        "An entry expires when now>=created+ttl. ttl is nonnegative. Return None for expired entries, "
        "otherwise return the stored JSON value unchanged; all times use the same supplied monotonic clock.",
        """
        def run(request):
            expired = request["now"] >= request["created"] + request["ttl"]
            return None if expired else request["value"]
        """,
        ('request["now"] >=', 'request["now"] >'),
        {
            "ignores_creation": (
                'request["created"] + request["ttl"]',
                'request["ttl"]',
            ),
            "expires_early": ('request["now"] >=', 'request["now"] + 1 >='),
        },
        examples(
            [
                (name, {"created": c, "ttl": ttl, "now": now, "value": value}, expected)
                for name, c, ttl, now, value, expected in [
                    ("fresh", 10, 5, 12, "ok", "ok"),
                    ("old", 10, 5, 16, "ok", None),
                    ("boundary", 10, 5, 15, "ok", None),
                    ("empty_value", 0, 10, 1, "", ""),
                    ("zero_ttl", 0, 0, 0, 1, None),
                    ("late_origin", 100, 10, 109, False, False),
                    ("fractional_boundary", 2, 0.5, 2.5, 7, None),
                    ("object", 0, 10, 9, {"x": 1}, {"x": 1}),
                    ("negative_origin", -4, 2, -2, 3, None),
                    ("before_boundary", 0, 2, 1, 0, 0),
                ]
            ]
        ),
        ("nist-sms",),
    )

    yield simple(
        "R08",
        "Delimiter collisions mix cache records from different tenants",
        "compound_cache_identity",
        "entries contains tenant/key/value records; later records replace earlier values for exactly the "
        "same pair. queries contains tenant/key records. Return values or None for missing pairs. "
        "Tenant and key strings are case sensitive and may contain colons.",
        """
        def identity(row):
            return (row["tenant"], row["key"])
        def run(request):
            cache = {identity(row): row["value"] for row in request["entries"]}
            return [cache.get(identity(row)) for row in request["queries"]]
        """,
        ('(row["tenant"], row["key"])', 'row["tenant"] + ":" + row["key"]'),
        {
            "key_only": ('(row["tenant"], row["key"])', 'row["key"]'),
            "casefold_tenants": (
                '(row["tenant"], row["key"])',
                '(row["tenant"].lower(), row["key"])',
            ),
        },
        examples(
            [
                (
                    name,
                    {
                        "entries": [
                            {"tenant": t, "key": k, "value": v} for t, k, v in entries
                        ],
                        "queries": [{"tenant": t, "key": k} for t, k in queries],
                    },
                    expected,
                )
                for name, entries, queries, expected in [
                    ("empty", [], [], []),
                    ("single", [("a", "x", 1)], [("a", "x")], [1]),
                    (
                        "collision",
                        [("a:b", "c", 1), ("a", "b:c", 2)],
                        [("a:b", "c"), ("a", "b:c")],
                        [1, 2],
                    ),
                    ("missing", [], [("a", "x")], [None]),
                    ("same_key", [("a", "x", 1), ("b", "x", 2)], [("a", "x")], [1]),
                    (
                        "case_sensitive",
                        [("A", "x", 1), ("a", "x", 2)],
                        [("A", "x")],
                        [1],
                    ),
                    (
                        "reverse_collision",
                        [("a", "b:c", 2), ("a:b", "c", 1)],
                        [("a", "b:c")],
                        [2],
                    ),
                    ("replace", [("a", "x", 1), ("a", "x", 3)], [("a", "x")], [3]),
                    (
                        "empty_components",
                        [("", "a:b", 1), (":a", "b", 2)],
                        [("", "a:b")],
                        [1],
                    ),
                    (
                        "unicode",
                        [("factory", "sensor-1", 0)],
                        [("factory", "sensor-1")],
                        [0],
                    ),
                ]
            ]
        ),
        ("nist-sms",),
    )

    yield simple(
        "R09",
        "Wall-clock adjustments corrupt request duration measurements",
        "monotonic_duration_source",
        "Return mono_end-mono_start seconds using monotonic timestamps. Those timestamps are finite and "
        "nondecreasing. wall_start/wall_end are diagnostic civil times and may jump in either direction.",
        """
        def run(request):
            return request["mono_end"] - request["mono_start"]
        """,
        (
            'request["mono_end"] - request["mono_start"]',
            'request["wall_end"] - request["wall_start"]',
        ),
        {
            "clamped_wall_time": (
                'request["mono_end"] - request["mono_start"]',
                'max(0, request["wall_end"] - request["wall_start"])',
            ),
            "absolute_wall_time": (
                'request["mono_end"] - request["mono_start"]',
                'abs(request["wall_end"] - request["wall_start"])',
            ),
        },
        examples(
            [
                (
                    name,
                    {"mono_start": s, "mono_end": e, "wall_start": ws, "wall_end": we},
                    expected,
                )
                for name, s, e, ws, we, expected in [
                    ("normal", 0, 2, 100, 102, 2),
                    ("zero", 1, 1, 100, 100, 0),
                    ("backward_jump", 1, 3, 100, 90, 2),
                    ("forward_jump", 1, 3, 100, 200, 2),
                    ("fractional", 2, 2.5, 100, 100.5, 0.5),
                    ("frozen_wall", 2, 7, 100, 100, 5),
                    ("large_epoch", 1000, 1003, 1000000, 1000100, 3),
                    ("repeated_backward", 0, 4, 100, 99, 4),
                    ("offset_independent", 50, 60, 0, 10, 10),
                    ("negative_wall", 0, 1, -2, -4, 1),
                ]
            ]
        ),
        ("nist-sms",),
    )

    yield simple(
        "R10",
        "Out-of-order acknowledgements skip an unprocessed sequence",
        "contiguous_ack_frontier",
        "cursor is the last contiguous acknowledged nonnegative sequence. acks contains positive sequence "
        "numbers, possibly unordered, repeated or older. Advance only over an uninterrupted run cursor+1, "
        "cursor+2, ...; acknowledgements beyond a gap must not advance the durable frontier.",
        """
        def run(request):
            cursor = request["cursor"]
            acknowledgements = set(request["acks"])
            while cursor + 1 in acknowledgements:
                cursor += 1
            return cursor
        """,
        (
            "while cursor + 1 in acknowledgements:\n        cursor += 1",
            "cursor = max(acknowledgements | {cursor})",
        ),
        {
            "only_one_step": (
                "while cursor + 1 in acknowledgements:",
                "if cursor + 1 in acknowledgements:",
            ),
            "one_behind": (
                "return cursor",
                'return max(request["cursor"], cursor - 1)',
            ),
        },
        examples(
            [
                (name, {"cursor": cursor, "acks": acks}, expected)
                for name, cursor, acks, expected in [
                    ("empty", 0, [], 0),
                    ("contiguous", 0, [1, 2, 3], 3),
                    ("gap", 0, [1, 3], 1),
                    ("duplicates", 0, [1, 1], 1),
                    ("no_first", 0, [2, 3], 0),
                    ("resume", 5, [8, 6], 6),
                    ("unordered", 3, [6, 4, 5], 6),
                    ("old", 5, [1, 2], 5),
                    ("fills_gap", 5, [7, 8, 6, 6], 8),
                    ("far_ahead", 10, [100], 10),
                ]
            ]
        ),
        ("mtconnect-2.0",),
    )
