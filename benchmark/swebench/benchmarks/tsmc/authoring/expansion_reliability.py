"""Six medium service-integrity tasks from the later policy cohort."""

from .easy import examples
from .schema import simple


def tasks():
    yield simple(
        "R21",
        "Idempotent commands conflict when JSON object keys are reordered",
        "canonical_idempotency_fingerprint",
        "commands has key, method, target, payload and result. First use of an idempotency key stores "
        "its fingerprint and result. Later identical commands return the stored result; different commands "
        "return 'conflict' and do not update storage. Fingerprint includes case-sensitive method, target and "
        "JSON payload, ignoring object key order recursively but preserving list order and numeric encoding. "
        "Results are strings other than 'conflict'. Return the response list.",
        """
        import json
        def run(request):
            stored, output = {}, []
            for command in request["commands"]:
                fingerprint = json.dumps([command["method"], command["target"], command["payload"]], sort_keys=True, separators=(",", ":"))
                key = command["key"]
                if key not in stored:
                    stored[key] = (fingerprint, command["result"])
                old, result = stored[key]
                output.append(result if old == fingerprint else "conflict")
            return output
        """,
        ("sort_keys=True", "sort_keys=False"),
        {
            "ignores_target": ('command["target"]', '""'),
            "ignores_method": ('command["method"]', '""'),
        },
        examples(
            [
                (
                    n,
                    {
                        "commands": [
                            dict(key=k, method=m, target=t, payload=p, result=r)
                            for k, m, t, p, r in rows
                        ]
                    },
                    v,
                )
                for n, rows, v in [
                    ("empty", [], []),
                    ("one", [("k", "POST", "/lot", {}, "a")], ["a"]),
                    (
                        "key_order",
                        [
                            ("k", "POST", "/lot", {"a": 1, "b": 2}, "a"),
                            ("k", "POST", "/lot", {"b": 2, "a": 1}, "b"),
                        ],
                        ["a", "a"],
                    ),
                    (
                        "same",
                        [
                            ("k", "POST", "/lot", {}, "a"),
                            ("k", "POST", "/lot", {}, "b"),
                        ],
                        ["a", "a"],
                    ),
                    (
                        "nested",
                        [
                            ("k", "POST", "/lot", {"x": {"a": 1, "b": 2}}, "a"),
                            ("k", "POST", "/lot", {"x": {"b": 2, "a": 1}}, "b"),
                        ],
                        ["a", "a"],
                    ),
                    (
                        "target",
                        [("k", "POST", "/a", {}, "a"), ("k", "POST", "/b", {}, "b")],
                        ["a", "conflict"],
                    ),
                    (
                        "method",
                        [("k", "POST", "/a", {}, "a"), ("k", "PUT", "/a", {}, "b")],
                        ["a", "conflict"],
                    ),
                    (
                        "list_order",
                        [
                            ("k", "POST", "/a", [1, 2], "a"),
                            ("k", "POST", "/a", [2, 1], "b"),
                        ],
                        ["a", "conflict"],
                    ),
                    (
                        "separate_keys",
                        [("k", "POST", "/a", {}, "a"), ("j", "POST", "/a", {}, "b")],
                        ["a", "b"],
                    ),
                    (
                        "conflict_keeps_original",
                        [
                            ("k", "POST", "/a", 1, "a"),
                            ("k", "POST", "/a", 2, "b"),
                            ("k", "POST", "/a", 1, "c"),
                        ],
                        ["a", "conflict", "a"],
                    ),
                ]
            ]
        ),
        ("production-log",),
        difficulty="medium",
        difficulty_reason="Canonicalize nested payloads while binding retries to the complete command identity.",
    )

    yield simple(
        "R24",
        "Failed order payment leaves material reservations consumed",
        "order_saga_compensation",
        "stock and balance are nonnegative integers. orders contain quantity>0, price>=0 and failure "
        "('none', 'charge', or 'after_charge'). Reject insufficient stock or balance without side effects. "
        "Otherwise reserve quantity, charge price, then complete. Injected failure must compensate all "
        "completed steps exactly once. Return accepted flags, stock and balance after all orders.",
        """
        def run(request):
            stock, balance, accepted = request["stock"], request["balance"], []
            for order in request["orders"]:
                quantity, price = order["quantity"], order["price"]
                if quantity > stock or price > balance:
                    accepted.append(False)
                    continue
                stock -= quantity
                charged = order["failure"] != "charge"
                if charged:
                    balance -= price
                valid = order["failure"] == "none"
                if not valid:
                    stock += quantity
                    if charged:
                        balance += price
                accepted.append(valid)
            return dict(accepted=accepted, stock=stock, balance=balance)
        """,
        ("stock += quantity", "pass"),
        {
            "refunds_unmade_charge": (
                "if charged:\n                balance += price",
                "if True:\n                balance += price",
            ),
            "no_refund": ("balance += price", "pass"),
        },
        examples(
            [
                (
                    n,
                    {
                        "stock": s,
                        "balance": b,
                        "orders": [
                            dict(quantity=q, price=p, failure=f) for q, p, f in rows
                        ],
                    },
                    dict(accepted=a, stock=stock, balance=balance),
                )
                for n, s, b, rows, a, stock, balance in [
                    ("empty", 5, 10, [], [], 5, 10),
                    ("success", 5, 10, [(2, 3, "none")], [True], 3, 7),
                    ("charge_fails", 5, 10, [(2, 3, "charge")], [False], 5, 10),
                    ("no_stock", 1, 10, [(2, 3, "none")], [False], 1, 10),
                    ("after_charge", 5, 10, [(2, 3, "after_charge")], [False], 5, 10),
                    (
                        "retry",
                        2,
                        3,
                        [(2, 3, "charge"), (2, 3, "none")],
                        [False, True],
                        0,
                        0,
                    ),
                    ("no_balance", 5, 1, [(2, 3, "none")], [False], 5, 1),
                    ("free_order", 2, 0, [(1, 0, "none")], [True], 1, 0),
                    (
                        "two_failures",
                        5,
                        10,
                        [(2, 3, "charge"), (2, 3, "after_charge")],
                        [False, False],
                        5,
                        10,
                    ),
                    (
                        "success_then_fail",
                        5,
                        10,
                        [(2, 3, "none"), (1, 2, "after_charge")],
                        [True, False],
                        3,
                        7,
                    ),
                ]
            ]
        ),
        ("bpi-2019",),
        difficulty="medium",
        difficulty_reason="Compensate only steps that completed and preserve state for later orders.",
    )

    yield simple(
        "R25",
        "Interrupted SQLite migrations leave half-upgraded sensor tables",
        "transactional_schema_migration",
        "Initial SQLite table measurements has one INTEGER value column populated from values. Migration "
        "atomically adds unit TEXT and fills it with 'Pa'. fail injects an exception after ALTER TABLE; "
        "rollback must restore the original schema and values. If retry is true, retry once without failure. "
        "Return columns and rows in insertion order. The migrate(connection, fail) function must use an "
        "actual SQLite transaction; no network or filesystem persistence is needed for this task.",
        """
        import sqlite3
        def migrate(connection, fail):
            connection.execute("BEGIN")
            try:
                connection.execute("ALTER TABLE measurements ADD COLUMN unit TEXT")
                if fail:
                    raise RuntimeError("injected interruption")
                connection.execute("UPDATE measurements SET unit = 'Pa'")
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        def run(request):
            connection = sqlite3.connect(":memory:")
            try:
                connection.execute("CREATE TABLE measurements (value INTEGER)")
                connection.executemany("INSERT INTO measurements VALUES (?)", [(v,) for v in request["values"]])
                connection.commit()
                try:
                    migrate(connection, request["fail"])
                except RuntimeError:
                    if request["retry"]:
                        migrate(connection, False)
                columns = [r[1] for r in connection.execute("PRAGMA table_info(measurements)")]
                rows = [list(r) for r in connection.execute("SELECT * FROM measurements ORDER BY rowid")]
                return dict(columns=columns, rows=rows)
            finally:
                connection.close()
        """,
        (
            "if fail:\n            raise",
            "connection.commit()\n        if fail:\n            raise",
        ),
        {
            "wrong_unit": ("SET unit = 'Pa'", "SET unit = 'kPa'"),
            "loses_measurements": (
                "connection.execute(\"UPDATE measurements SET unit = 'Pa'\")",
                'connection.execute("DELETE FROM measurements")',
            ),
        },
        examples(
            [
                (
                    n,
                    {"values": values, "fail": fail, "retry": retry},
                    dict(columns=cols, rows=rows),
                )
                for n, values, fail, retry, cols, rows in [
                    ("empty", [], False, False, ["value", "unit"], []),
                    (
                        "success",
                        [1, 2],
                        False,
                        False,
                        ["value", "unit"],
                        [[1, "Pa"], [2, "Pa"]],
                    ),
                    ("rollback", [1], True, False, ["value"], [[1]]),
                    ("zero", [0], False, False, ["value", "unit"], [[0, "Pa"]]),
                    ("retry", [1], True, True, ["value", "unit"], [[1, "Pa"]]),
                    ("empty_rollback", [], True, False, ["value"], []),
                    ("empty_retry", [], True, True, ["value", "unit"], []),
                    (
                        "preserve_order",
                        [3, 1, 2],
                        True,
                        True,
                        ["value", "unit"],
                        [[3, "Pa"], [1, "Pa"], [2, "Pa"]],
                    ),
                    (
                        "duplicates",
                        [1, 1],
                        False,
                        True,
                        ["value", "unit"],
                        [[1, "Pa"], [1, "Pa"]],
                    ),
                    ("negative", [-1, 0], True, False, ["value"], [[-1], [0]]),
                ]
            ]
        ),
        ("nist-sms",),
        difficulty="medium",
        difficulty_reason="Keep SQLite DDL and data changes in one rollback boundary and support a clean retry.",
    )

    yield simple(
        "R26",
        "Reordered batch RPC responses attach results to the wrong work orders",
        "rpc_response_correlation",
        "ids is an ordered unique list of request ids. responses has unique id/value pairs in arbitrary "
        "order, possibly missing requests or containing unrelated ids. Return values in request order, "
        "using None for missing responses. Preserve zero, false and null values.",
        """
        def run(request):
            responses = {r["id"]: r["value"] for r in request["responses"]}
            return [responses.get(key) for key in request["ids"]]
        """,
        (
            'responses = {r["id"]: r["value"] for r in request["responses"]}',
            'responses = {key: row["value"] for key, row in zip(request["ids"], request["responses"])}',
        ),
        {
            "drops_zero": ("responses.get(key)", "responses.get(key) or None"),
            "sorts_requests": (
                'for key in request["ids"]',
                'for key in sorted(request["ids"])',
            ),
        },
        examples(
            [
                (
                    n,
                    {"ids": ids, "responses": [dict(id=k, value=v) for k, v in rows]},
                    expected,
                )
                for n, ids, rows, expected in [
                    ("empty", [], [], []),
                    ("one", ["a"], [("a", 2)], [2]),
                    ("reverse", ["a", "b"], [("b", 2), ("a", 1)], [1, 2]),
                    ("missing", ["a"], [], [None]),
                    ("partial", ["a", "b"], [("b", 2)], [None, 2]),
                    ("unrelated", ["a"], [("z", 9)], [None]),
                    ("zero", ["a"], [("a", 0)], [0]),
                    ("false", ["a"], [("a", False)], [False]),
                    ("request_order", ["b", "a"], [("a", 1), ("b", 2)], [2, 1]),
                    ("null", ["a", "b"], [("b", None), ("a", 1)], [1, None]),
                ]
            ]
        ),
        ("nist-sms",),
        difficulty="medium",
        difficulty_reason="Correlate partial batches by identity while preserving requested order and valid falsey data.",
    )

    yield simple(
        "R27",
        "Deduplication cleanup runs ahead of the slowest consumer",
        "consumer_frontier_safe_retention",
        "records contains unique id/offset entries with offset>=0. consumers contains active boolean and "
        "ack, the last durably processed offset (>=-1). Delete records only when offset<=every active "
        "consumer's ack. With no active consumers retain everything. Return retained ids in input order.",
        """
        def run(request):
            frontiers = [c["ack"] for c in request["consumers"] if c["active"]]
            safe = min(frontiers) if frontiers else -1
            return [r["id"] for r in request["records"] if r["offset"] > safe]
        """,
        ("min(frontiers)", "max(frontiers)"),
        {
            "includes_inactive": ('if c["active"]', "if True"),
            "deletes_next": ('r["offset"] > safe', 'r["offset"] > safe + 1'),
        },
        examples(
            [
                (
                    n,
                    {
                        "records": [
                            dict(id=str(i), offset=o) for i, o in enumerate(offsets)
                        ],
                        "consumers": [dict(active=a, ack=k) for a, k in consumers],
                    },
                    v,
                )
                for n, offsets, consumers, v in [
                    ("empty", [], [], []),
                    ("one", [0, 1, 2], [(True, 1)], ["2"]),
                    ("slow", [0, 1, 2], [(True, 0), (True, 2)], ["1", "2"]),
                    ("no_consumers", [0, 1], [], ["0", "1"]),
                    ("unstarted", [0, 1], [(True, -1), (True, 1)], ["0", "1"]),
                    ("inactive", [0, 1, 2], [(True, 1), (False, -1)], ["2"]),
                    ("all_inactive", [0, 1], [(False, 5)], ["0", "1"]),
                    ("equal", [0, 1, 2], [(True, 1), (True, 1)], ["2"]),
                    ("input_order", [3, 1, 2], [(True, 1)], ["0", "2"]),
                    (
                        "three_consumers",
                        [0, 1, 2, 3],
                        [(True, 3), (True, 1), (True, 2)],
                        ["2", "3"],
                    ),
                ]
            ]
        ),
        ("mtconnect-2.0",),
        difficulty="medium",
        difficulty_reason="Derive a safe retention frontier from all active consumers, including initial and inactive states.",
    )

    yield simple(
        "R28",
        "Journal recovery treats corruption in committed records as a torn tail",
        "journal_corruption_boundary",
        "lines are journal records 'sequence|payload|crc', where crc is eight lowercase hexadecimal "
        "digits for zlib.crc32 of UTF-8 'sequence|payload'. Sequences start at 1 and are contiguous; payload "
        "has no pipes. Ignore at most one malformed or bad-checksum final line as a torn append. "
        "Malformed earlier lines or valid records with noncontiguous sequence raise ValueError. "
        "Return payloads of recovered records. A valid final record must never be discarded.",
        """
        import zlib
        def run(request):
            output = []
            for index, line in enumerate(request["lines"]):
                try:
                    sequence, payload, checksum = line.split("|")
                    valid = checksum == format(zlib.crc32((sequence + "|" + payload).encode()), "08x")
                    number = int(sequence)
                    if not valid:
                        raise ValueError("checksum mismatch")
                except ValueError:
                    if index == len(request["lines"]) - 1:
                        break
                    raise
                if number != len(output) + 1:
                    raise ValueError("noncontiguous sequence")
                output.append(payload)
            return output
        """,
        ('if index == len(request["lines"]) - 1:', "if True:"),
        {
            "rejects_torn_tail": (
                'if index == len(request["lines"]) - 1:',
                "if False:",
            ),
            "ignores_sequence_gap": ("if number != len(output) + 1:", "if False:"),
        },
        journal_cases(),
        ("nist-sms",),
        difficulty="medium",
        difficulty_reason="Distinguish incomplete final append from interior corruption and sequence discontinuity.",
    )


def journal_cases():
    import zlib
    from .schema import Case

    # CRC construction encodes fixtures; expected recovery results remain literal.
    def record(number, payload):
        text = f"{number}|{payload}"
        return f"{text}|{zlib.crc32(text.encode()):08x}"

    a, b, c = record(1, "a"), record(2, "b"), record(3, "c")
    return [
        Case("empty", {"lines": []}, [], public=True),
        Case("valid", {"lines": [a, b]}, ["a", "b"], public=True),
        Case(
            "interior_corruption",
            {"lines": [a, "broken", c]},
            error="ValueError",
            public=True,
        ),
        Case("torn_tail", {"lines": [a, "broken"]}, ["a"], public=True),
        Case("bad_crc_inside", {"lines": ["1|a|00000000", b]}, error="ValueError"),
        Case("bad_crc_tail", {"lines": [a, "2|b|00000000"]}, ["a"]),
        Case("gap", {"lines": [a, c]}, error="ValueError"),
        Case("duplicate", {"lines": [a, a]}, error="ValueError"),
        Case("valid_tail", {"lines": [a, b, c]}, ["a", "b", "c"]),
        Case("first_sequence", {"lines": [b]}, error="ValueError"),
    ]
