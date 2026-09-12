"""Five easy tasks authored after the 20/70/10 difficulty policy was set."""

from .easy import examples
from .schema import simple


def tasks():
    yield simple(
        "F20",
        "Goods receipt reversals increase received quantity",
        "signed_goods_receipt_quantity",
        "events contains receipt or reversal records with nonnegative integer quantity. Sum receipts "
        "positively and reversals negatively. Return the signed net quantity, including negative totals.",
        """
        def run(request):
            return sum(e["quantity"] if e["type"] == "receipt" else -e["quantity"] for e in request["events"])
        """,
        ('else -e["quantity"]', 'else e["quantity"]'),
        {
            "clamps_negative": (
                'return sum(e["quantity"] if e["type"] == "receipt" else -e["quantity"] for e in request["events"])',
                'return max(0, sum(e["quantity"] if e["type"] == "receipt" else -e["quantity"] for e in request["events"]))',
            ),
            "drops_reversals": ('else -e["quantity"]', "else 0"),
        },
        examples(
            [
                (n, {"events": [dict(type=t, quantity=q) for t, q in rows]}, v)
                for n, rows, v in [
                    ("empty", [], 0),
                    ("receipt", [("receipt", 4)], 4),
                    ("reversal", [("reversal", 2)], -2),
                    ("zero", [("receipt", 0)], 0),
                    ("net", [("receipt", 5), ("reversal", 2)], 3),
                    ("cancel", [("receipt", 5), ("reversal", 5)], 0),
                    ("multiple", [("receipt", 2), ("receipt", 3), ("reversal", 1)], 4),
                    ("all_reversed", [("reversal", 1), ("reversal", 2)], -3),
                    ("zero_reversal", [("reversal", 0)], 0),
                    ("later_receipt", [("reversal", 5), ("receipt", 2)], -3),
                ]
            ]
        ),
        ("bpi-2019",),
    )

    yield simple(
        "A20",
        "SECOM-style failure labels are interpreted as booleans",
        "signed_quality_label_decoding",
        "labels contains -1 for pass and +1 for fail. Return failure booleans in the same order. "
        "Only these two integer labels are valid; label magnitude is not a probability.",
        """
        def run(request):
            return [label == 1 for label in request["labels"]]
        """,
        ("label == 1", "bool(label)"),
        {
            "reversed_labels": ("label == 1", "label == -1"),
            "all_pass": ("label == 1", "False"),
        },
        examples(
            [
                (n, {"labels": labels}, v)
                for n, labels, v in [
                    ("empty", [], []),
                    ("fail", [1], [True]),
                    ("pass", [-1], [False]),
                    ("mixed", [-1, 1], [False, True]),
                    ("reverse", [1, -1], [True, False]),
                    ("all_pass", [-1, -1], [False, False]),
                    ("all_fail", [1, 1], [True, True]),
                    ("rare_fail", [-1, -1, 1, -1], [False, False, True, False]),
                    ("alternating", [1, -1, 1], [True, False, True]),
                    ("last_fail", [-1, -1, -1, 1], [False, False, False, True]),
                ]
            ]
        ),
        ("secom",),
    )

    yield simple(
        "A22",
        "Pressure units are converted in the wrong direction",
        "pressure_unit_normalization",
        "measurements contains value and unit, one of Pa, kPa or bar. Return values in Pa using "
        "1 kPa=1000 Pa and 1 bar=100000 Pa. Preserve zero and negative gauge pressures and input order.",
        """
        def run(request):
            scales = {"Pa": 1, "kPa": 1000, "bar": 100000}
            return [row["value"] * scales[row["unit"]] for row in request["measurements"]]
        """,
        ('"bar": 100000', '"bar": 1000'),
        {
            "kilopascal_scale": ('"kPa": 1000', '"kPa": 1'),
            "absolute_pressure": ('row["value"] *', 'abs(row["value"]) *'),
        },
        examples(
            [
                (n, {"measurements": [dict(unit=u, value=x) for u, x in rows]}, v)
                for n, rows, v in [
                    ("empty", [], []),
                    ("pascal", [("Pa", 2)], [2]),
                    ("bar", [("bar", 2)], [200000]),
                    ("kilopascal", [("kPa", 2)], [2000]),
                    ("half_bar", [("bar", 0.5)], [50000]),
                    ("negative", [("kPa", -1)], [-1000]),
                    ("zero", [("bar", 0)], [0]),
                    ("mixed", [("bar", 1), ("Pa", 1), ("kPa", 1)], [100000, 1, 1000]),
                    ("negative_bar", [("bar", -2)], [-200000]),
                    ("fractional", [("kPa", 0.25)], [250]),
                ]
            ]
        ),
        ("zema-hydraulic",),
    )

    yield simple(
        "R20",
        "Boolean timeout settings bypass integer validation",
        "strict_timeout_configuration",
        "For every value in timeouts, return whether it is an integer from 1 through 300 inclusive. JSON booleans, strings, "
        "null, fractional and integral floats are invalid; Python bool being an int subclass must not admit it.",
        """
        def run(request):
            return [type(value) is int and 1 <= value <= 300 for value in request["timeouts"]]
        """,
        ("type(value) is int", "isinstance(value, int)"),
        {
            "excludes_max": ("value <= 300", "value < 300"),
            "accepts_zero": ("1 <= value", "0 <= value"),
        },
        examples(
            [
                (n, {"timeouts": x}, v)
                for n, x, v in [
                    ("normal", [30], [True]),
                    ("null", [None], [False]),
                    ("boolean", [True], [False]),
                    ("text", ["30"], [False]),
                    ("max", [300], [True]),
                    ("zero", [0], [False]),
                    ("float", [1.0], [False]),
                    ("min", [1], [True]),
                    ("mixed", [30, True, False], [True, False, False]),
                    ("over", [301], [False]),
                ]
            ]
        ),
        ("nist-sms",),
    )

    yield simple(
        "R23",
        "MTConnect sample cursors advance past the advertised next sequence",
        "advertised_sample_cursor",
        "Each response has nextSequence, the sequence to request next, and observations with sequence "
        "numbers. Return response nextSequence values unchanged, including empty filtered responses. "
        "The header already identifies the first unread sequence; it is not the last observation.",
        """
        def run(request):
            return [response["nextSequence"] for response in request["responses"]]
        """,
        (
            'response["nextSequence"]',
            '(max(response["observations"]) + 1 if response["observations"] else 1)',
        ),
        {
            "one_past_header": (
                'response["nextSequence"]',
                'response["nextSequence"] + 1',
            ),
            "previous_sequence": (
                'response["nextSequence"]',
                'max(1, response["nextSequence"] - 1)',
            ),
        },
        examples(
            [
                (
                    n,
                    {
                        "responses": [
                            dict(nextSequence=s, observations=o) for s, o in rows
                        ]
                    },
                    v,
                )
                for n, rows, v in [
                    ("empty_batch", [], []),
                    ("unchanged_empty", [(5, [])], [5]),
                    ("normal", [(4, [1, 2, 3])], [4]),
                    ("filtered", [(10, [3, 7])], [10]),
                    ("empty_filtered", [(20, [])], [20]),
                    ("one", [(2, [1])], [2]),
                    ("resumed", [(101, [100])], [101]),
                    ("multiple", [(4, [1, 2, 3]), (8, [4, 7])], [4, 8]),
                    ("no_observation", [(1, [])], [1]),
                    ("large", [(1000001, [1000000])], [1000001]),
                ]
            ]
        ),
        ("mtconnect-2.0",),
    )
