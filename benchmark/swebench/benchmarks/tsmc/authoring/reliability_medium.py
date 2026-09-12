"""Factory service retry, queue, cache and lifecycle repairs."""

from .easy import examples
from .schema import simple


def tasks():
    yield simple(
        "R11",
        "HTTP date retry delays ignore the response clock",
        "retry_after_http_date",
        "Retry-After is either nonnegative integer seconds or an RFC 7231 HTTP date. now is an HTTP date "
        "in GMT. Return max(0, retry_time-now) seconds for dates, literal seconds for integers, and None "
        "for malformed or negative headers. Strip surrounding whitespace.",
        """
        from email.utils import parsedate_to_datetime
        def run(request):
            header = request["header"].strip()
            if header.isascii() and header.isdigit():
                return int(header)
            try:
                retry = parsedate_to_datetime(header)
                now = parsedate_to_datetime(request["now"])
                return max(0, (retry - now).total_seconds())
            except (TypeError, ValueError, OverflowError):
                return None
        """,
        ("(retry - now).total_seconds()", "retry.timestamp()"),
        {
            "negative_past": (
                "max(0, (retry - now).total_seconds())",
                "(retry - now).total_seconds()",
            ),
            "caps_large_seconds": ("return int(header)", "return min(60, int(header))"),
        },
        examples(
            [
                (n, {"header": h, "now": "Wed, 01 Jan 2025 00:00:00 GMT"}, v)
                for n, h, v in [
                    ("seconds", "15", 15),
                    ("zero", "0", 0),
                    ("date", "Wed, 01 Jan 2025 00:00:05 GMT", 5),
                    ("malformed", "later", None),
                    ("past", "Tue, 31 Dec 2024 23:59:59 GMT", 0),
                    ("boundary", "Wed, 01 Jan 2025 00:00:00 GMT", 0),
                    ("day", "Thu, 02 Jan 2025 00:00:00 GMT", 86400),
                    ("whitespace", " 120 ", 120),
                    ("negative", "-1", None),
                    ("fractional", "1.5", None),
                ]
            ]
        ),
        ("nist-sms",),
        difficulty="medium",
        difficulty_reason="Distinguish two protocol formats and normalize absolute dates against a supplied clock.",
    )

    yield simple(
        "R12",
        "Poison work orders prevent later messages from being processed",
        "poison_message_dead_letter_progress",
        "messages is an ordered list of unique id/valid records. For each message, valid is a JSON boolean. "
        "Invalid messages fail exactly max_attempts times then enter dead_letter. Valid messages process once. "
        "Return processed ids, dead_letter ids and attempts by id. max_attempts is positive; continue past poison.",
        """
        def run(request):
            processed, dead, attempts = [], [], {}
            for message in request["messages"]:
                key = message["id"]
                attempts[key] = 1 if message["valid"] else request["max_attempts"]
                if message["valid"]:
                    processed.append(key)
                else:
                    dead.append(key)
            return dict(processed=processed, dead_letter=dead, attempts=attempts)
        """,
        ("dead.append(key)", "dead.append(key)\n            break"),
        {
            "too_many_attempts": (
                'else request["max_attempts"]',
                'else request["max_attempts"] + 1',
            ),
            "drops_dead_letter": ("dead.append(key)", "pass"),
        },
        examples(
            [
                (
                    n,
                    {
                        "messages": [
                            dict(id=str(i), valid=b) for i, b in enumerate(values)
                        ],
                        "max_attempts": limit,
                    },
                    dict(processed=p, dead_letter=d, attempts=a),
                )
                for n, values, limit, p, d, a in [
                    ("empty", [], 2, [], [], {}),
                    ("valid", [True], 2, ["0"], [], {"0": 1}),
                    ("poison_first", [False, True], 2, ["1"], ["0"], {"0": 2, "1": 1}),
                    ("poison_only", [False], 2, [], ["0"], {"0": 2}),
                    ("two_poison", [False, False], 3, [], ["0", "1"], {"0": 3, "1": 3}),
                    (
                        "middle",
                        [True, False, True],
                        2,
                        ["0", "2"],
                        ["1"],
                        {"0": 1, "1": 2, "2": 1},
                    ),
                    ("one_attempt", [False, True], 1, ["1"], ["0"], {"0": 1, "1": 1}),
                    ("all_good", [True, True], 3, ["0", "1"], [], {"0": 1, "1": 1}),
                    ("last", [True, False], 4, ["0"], ["1"], {"0": 1, "1": 4}),
                    (
                        "alternating",
                        [False, True, False],
                        2,
                        ["1"],
                        ["0", "2"],
                        {"0": 2, "1": 1, "2": 2},
                    ),
                ]
            ]
        ),
        ("production-log",),
        difficulty="medium",
        difficulty_reason="Preserve queue progress and terminal disposition after retry exhaustion.",
    )

    yield simple(
        "R13",
        "Cancelling one telemetry waiter cancels shared requests",
        "singleflight_waiter_cancellation",
        "The SingleFlight.get(key, loader) async API shares one running loader task per key. Cancelling "
        "a waiter must not cancel the shared loader or other waiters. Failed or completed tasks must be "
        "removed before the next independent request. run performs deterministic rounds: keys lists "
        "concurrent callers, cancel lists caller indices. Return per-round results ('cancelled' for cancelled "
        "waiters, otherwise the key) and total loader calls by key. Keys are strings. No wall-clock sleeps.",
        """
        import asyncio
        class SingleFlight:
            def __init__(self):
                self.pending = {}
            def discard(self, key, task):
                if self.pending.get(key) is task:
                    self.pending.pop(key)
            async def get(self, key, loader):
                if key not in self.pending:
                    self.pending[key] = asyncio.create_task(loader(key))
                    self.pending[key].add_done_callback(lambda done: self.discard(key, done))
                task = self.pending[key]
                try:
                    return await asyncio.shield(task)
                finally:
                    if task.done() and self.pending.get(key) is task:
                        del self.pending[key]
        async def exercise(request):
            flight, calls, output = SingleFlight(), {}, []
            for round in request["rounds"]:
                gate = asyncio.Event()
                async def loader(key):
                    calls[key] = calls.get(key, 0) + 1
                    await gate.wait()
                    return key
                waiters = [asyncio.create_task(flight.get(key, loader)) for key in round["keys"]]
                await asyncio.sleep(0)
                await asyncio.sleep(0)
                for index in round["cancel"]:
                    waiters[index].cancel()
                await asyncio.sleep(0)
                gate.set()
                results = await asyncio.gather(*waiters, return_exceptions=True)
                output.append(["cancelled" if isinstance(r, asyncio.CancelledError) else r for r in results])
                for key, task in list(flight.pending.items()):
                    await asyncio.gather(task, return_exceptions=True)
                    if task.done():
                        flight.pending.pop(key, None)
            return dict(results=output, calls=calls)
        def run(request):
            return asyncio.run(exercise(request))
        """,
        ("return await asyncio.shield(task)", "return await task"),
        {
            "no_sharing": ("if key not in self.pending:", "if True:"),
            "single_global_key": (
                "if key not in self.pending:",
                'key = "shared"\n        if key not in self.pending:',
            ),
        },
        examples(
            [
                (
                    n,
                    {
                        "rounds": [
                            dict(keys=keys, cancel=cancel) for keys, cancel in rounds
                        ]
                    },
                    dict(results=res, calls=calls),
                )
                for n, rounds, res, calls in [
                    ("empty", [], [], {}),
                    ("one", [(["a"], [])], [["a"]], {"a": 1}),
                    ("cancel_one", [(["a", "a"], [0])], [["cancelled", "a"]], {"a": 1}),
                    ("shared", [(["a", "a"], [])], [["a", "a"]], {"a": 1}),
                    (
                        "cancel_second",
                        [(["a", "a"], [1])],
                        [["a", "cancelled"]],
                        {"a": 1},
                    ),
                    (
                        "three",
                        [(["a", "a", "a"], [1])],
                        [["a", "cancelled", "a"]],
                        {"a": 1},
                    ),
                    ("distinct", [(["a", "b"], [])], [["a", "b"]], {"a": 1, "b": 1}),
                    ("new_round", [(["a"], []), (["a"], [])], [["a"], ["a"]], {"a": 2}),
                    (
                        "cancel_all",
                        [(["a", "a"], [0, 1])],
                        [["cancelled", "cancelled"]],
                        {"a": 1},
                    ),
                    (
                        "mixed",
                        [(["a", "b", "a"], [0])],
                        [["cancelled", "b", "a"]],
                        {"a": 1, "b": 1},
                    ),
                ]
            ]
        ),
        ("nist-sms",),
        difficulty="medium",
        difficulty_reason="Reason about real asyncio cancellation propagation and shared task ownership.",
    )

    yield simple(
        "R14",
        "Former lease owners renew another worker's reservation",
        "owner_checked_lease_renewal",
        "The initial lease has owner and expires. Each renewal supplies owner, now and ttl>0. Accept only "
        "the current owner while now<expires; set expires=now+ttl on acceptance. Return accepted flags and "
        "the final lease. Renewal times are nondecreasing and use a supplied monotonic clock.",
        """
        def run(request):
            lease = dict(request["lease"])
            accepted = []
            for renewal in request["renewals"]:
                valid = renewal["owner"] == lease["owner"] and renewal["now"] < lease["expires"]
                if valid:
                    lease["expires"] = renewal["now"] + renewal["ttl"]
                accepted.append(valid)
            return dict(accepted=accepted, lease=lease)
        """,
        ('renewal["owner"] == lease["owner"] and ', ""),
        {
            "expired_owner": (
                'renewal["now"] < lease["expires"]',
                'renewal["now"] <= lease["expires"]',
            ),
            "extends_old_expiry": (
                'renewal["now"] + renewal["ttl"]',
                'lease["expires"] + renewal["ttl"]',
            ),
        },
        examples(
            [
                (
                    n,
                    {
                        "lease": {"owner": "a", "expires": 10},
                        "renewals": [
                            dict(owner=o, now=t, ttl=ttl) for o, t, ttl in rows
                        ],
                    },
                    dict(accepted=a, lease=dict(owner="a", expires=e)),
                )
                for n, rows, a, e in [
                    ("empty", [], [], 10),
                    ("owner", [("a", 5, 10)], [True], 15),
                    ("other", [("b", 5, 10)], [False], 10),
                    ("expired", [("a", 11, 10)], [False], 10),
                    ("boundary", [("a", 10, 10)], [False], 10),
                    ("after_rejection", [("b", 5, 20), ("a", 6, 5)], [False, True], 11),
                    ("two_owners", [("b", 1, 20), ("c", 2, 20)], [False, False], 10),
                    ("shorten", [("a", 5, 1)], [True], 6),
                    ("renew_again", [("a", 9, 5), ("a", 12, 5)], [True, True], 17),
                    ("wrong_expired", [("b", 10, 20)], [False], 10),
                ]
            ]
        ),
        ("nist-sms",),
        difficulty="medium",
        difficulty_reason="Combine ownership and expiration checks before state mutation.",
    )

    yield simple(
        "R15",
        "Oversized cache writes evict useful entries before rejection",
        "weighted_lru_admission",
        "capacity is nonnegative. Process put(key,weight) and get(key) operations. Positive integer weights "
        "count toward capacity. Reject oversized puts without changing anything. Other puts replace and "
        "become most recent, evicting oldest until within capacity. Successful gets promote; missing gets do "
        "nothing. Return keys oldest-to-newest and total weight.",
        """
        from collections import OrderedDict
        def run(request):
            cache = OrderedDict()
            for operation in request["operations"]:
                key = operation["key"]
                if operation["op"] == "get":
                    if key in cache:
                        cache.move_to_end(key)
                else:
                    weight = operation["weight"]
                    if weight > request["capacity"]:
                        continue
                    cache.pop(key, None)
                    cache[key] = weight
                    while sum(cache.values()) > request["capacity"]:
                        cache.popitem(last=False)
            return dict(keys=list(cache), weight=sum(cache.values()))
        """,
        ('if weight > request["capacity"]:', "if False:"),
        {
            "evicts_newest": ("popitem(last=False)", "popitem(last=True)"),
            "get_does_not_promote": ("cache.move_to_end(key)", "pass"),
        },
        examples(
            [
                (
                    n,
                    {
                        "capacity": 4,
                        "operations": [
                            dict(op="put", key=k, weight=w)
                            if w is not None
                            else dict(op="get", key=k)
                            for k, w in ops
                        ],
                    },
                    dict(keys=keys, weight=weight),
                )
                for n, ops, keys, weight in [
                    ("empty", [], [], 0),
                    ("one", [("a", 2)], ["a"], 2),
                    ("oversized", [("a", 2), ("b", 5)], ["a"], 2),
                    ("evict", [("a", 3), ("b", 2)], ["b"], 2),
                    ("replace_oversized", [("a", 2), ("a", 5)], ["a"], 2),
                    (
                        "get_promotes",
                        [("a", 2), ("b", 2), ("a", None), ("c", 2)],
                        ["a", "c"],
                        4,
                    ),
                    ("replace", [("a", 3), ("a", 1)], ["a"], 1),
                    ("missing_get", [("a", 2), ("z", None)], ["a"], 2),
                    ("exact", [("a", 2), ("b", 2)], ["a", "b"], 4),
                    ("replace_promotes", [("a", 1), ("b", 2), ("a", 2)], ["b", "a"], 4),
                ]
            ]
        ),
        ("nist-sms",),
        difficulty="medium",
        difficulty_reason="Make admission and replacement decisions before weighted eviction and recency updates.",
    )

    yield simple(
        "R16",
        "Successful circuit-breaker probes retain old failures",
        "circuit_breaker_failure_reset",
        "events contains call records with now and success. A closed breaker opens after threshold consecutive "
        "failures. While open, reject calls until now>=opened_at+cooldown. The first eligible call is a probe: "
        "success closes and resets failures, failure reopens at now. Return accepted flags, state and failures. "
        "Times are nondecreasing, threshold>=1 and cooldown>0.",
        """
        def run(request):
            state, failures, opened = "closed", 0, None
            accepted = []
            for event in request["events"]:
                if state == "open" and event["now"] < opened + request["cooldown"]:
                    accepted.append(False)
                    continue
                accepted.append(True)
                if event["success"]:
                    state, failures = "closed", 0
                else:
                    failures += 1
                    if failures >= request["threshold"]:
                        state, opened = "open", event["now"]
            return dict(accepted=accepted, state=state, failures=failures)
        """,
        ('state, failures = "closed", 0', 'state = "closed"'),
        {
            "late_probe": ('event["now"] < opened', 'event["now"] <= opened'),
            "early_open": (
                'failures >= request["threshold"]',
                'failures >= request["threshold"] - 1',
            ),
        },
        examples(
            [
                (
                    n,
                    {
                        "threshold": 2,
                        "cooldown": 5,
                        "events": [dict(now=t, success=s) for t, s in ev],
                    },
                    dict(accepted=a, state=st, failures=f),
                )
                for n, ev, a, st, f in [
                    ("empty", [], [], "closed", 0),
                    ("success", [(0, True)], [True], "closed", 0),
                    ("reset", [(0, False), (1, True)], [True, True], "closed", 0),
                    ("opens", [(0, False), (1, False)], [True, True], "open", 2),
                    (
                        "blocked",
                        [(0, False), (1, False), (2, True)],
                        [True, True, False],
                        "open",
                        2,
                    ),
                    (
                        "probe",
                        [(0, False), (1, False), (6, True)],
                        [True, True, True],
                        "closed",
                        0,
                    ),
                    (
                        "after_probe",
                        [(0, False), (1, False), (6, True), (7, False)],
                        [True] * 4,
                        "closed",
                        1,
                    ),
                    (
                        "interrupted_streak",
                        [(0, False), (1, True), (2, False)],
                        [True] * 3,
                        "closed",
                        1,
                    ),
                    (
                        "failed_probe",
                        [(0, False), (1, False), (6, False), (7, True)],
                        [True, True, True, False],
                        "open",
                        3,
                    ),
                    ("one_failure", [(0, False)], [True], "closed", 1),
                ]
            ]
        ),
        ("nist-sms",),
        difficulty="medium",
        difficulty_reason="Maintain failure streak and cooldown transitions across recovery probes.",
    )

    yield simple(
        "R17",
        "Frequent rate-limit checks lose fractional token refills",
        "fractional_token_bucket",
        "capacity>=1 and rate>0 are integers. Initially the bucket is full at time zero. For nondecreasing "
        "integer request times, refill min(capacity,tokens+(now-last)*rate), then consume one if available. "
        "times use milliseconds and rate uses tokens/second. Preserve fractional credit. Return accepted and "
        "remaining milli-tokens as integers (1000 per token).",
        """
        def run(request):
            tokens, last, accepted = request["capacity"] * 1000, 0, []
            for now in request["times"]:
                tokens = min(request["capacity"] * 1000, tokens + (now - last) * request["rate"])
                last = now
                valid = tokens >= 1000
                if valid:
                    tokens -= 1000
                accepted.append(valid)
            return dict(accepted=accepted, milli_tokens=tokens)
        """,
        (
            '(now - last) * request["rate"]',
            '((now - last) * request["rate"] // 1000) * 1000',
        ),
        {
            "uncapped": (
                'min(request["capacity"] * 1000, tokens + (now - last) * request["rate"])',
                'tokens + (now - last) * request["rate"]',
            ),
            "strict_token": ("tokens >= 1000", "tokens > 1000"),
        },
        examples(
            [
                (
                    n,
                    {"capacity": c, "rate": r, "times": t},
                    dict(accepted=a, milli_tokens=v),
                )
                for n, c, r, t, a, v in [
                    ("empty", 1, 1, [], [], 1000),
                    ("initial", 1, 1, [0], [True], 0),
                    ("fraction", 1, 1, [0, 500], [True, False], 500),
                    ("full_second", 1, 1, [0, 1000], [True, True], 0),
                    (
                        "many_checks",
                        1,
                        1,
                        [0, 250, 500, 750, 1000],
                        [True, False, False, False, True],
                        0,
                    ),
                    ("cap", 1, 1, [10000], [True], 0),
                    ("twice_rate", 1, 2, [0, 250, 500], [True, False, True], 0),
                    ("burst", 2, 1, [0, 0, 0], [True, True, False], 0),
                    ("partial_after_success", 2, 1, [0, 500], [True, True], 500),
                    ("same_time", 1, 1, [0, 0], [True, False], 0),
                ]
            ]
        ),
        ("nist-sms",),
        difficulty="medium",
        difficulty_reason="Preserve fractional refill across observations while enforcing burst capacity.",
    )

    yield simple(
        "R18",
        "Cancelled semaphore waiters block the admission queue",
        "fifo_weighted_semaphore_cancellation",
        "capacity is positive. Process enqueue(id,weight), cancel(id) for waiting ids, and release(id) for "
        "active ids. Weights are 1..capacity, ids unique across enqueues. After every operation, admit as many "
        "head waiters as fit; never bypass a heavier head. Unknown cancel/release is a no-op. Return "
        "admission history, sorted active ids and pending ids in FIFO order.",
        """
        def run(request):
            queue, active, admitted = [], {}, []
            for op in request["operations"]:
                if op["op"] == "enqueue":
                    queue.append((op["id"], op["weight"]))
                elif op["op"] == "cancel":
                    queue = [entry for entry in queue if entry[0] != op["id"]]
                else:
                    active.pop(op["id"], None)
                while queue and sum(active.values()) + queue[0][1] <= request["capacity"]:
                    key, weight = queue.pop(0)
                    active[key] = weight
                    admitted.append(key)
            return dict(admitted=admitted, active=sorted(active), pending=[k for k, _ in queue])
        """,
        ('queue = [entry for entry in queue if entry[0] != op["id"]]', "pass"),
        {
            "strict_capacity": ('<= request["capacity"]', '< request["capacity"]'),
            "release_leaks": ('active.pop(op["id"], None)', "pass"),
        },
        examples(
            [
                (
                    n,
                    {
                        "capacity": 3,
                        "operations": [
                            dict(op=o, id=k, **({"weight": w} if w else {}))
                            for o, k, w in ops
                        ],
                    },
                    dict(admitted=a, active=active, pending=p),
                )
                for n, ops, a, active, p in [
                    ("empty", [], [], [], []),
                    ("one", [("enqueue", "a", 2)], ["a"], ["a"], []),
                    (
                        "cancel",
                        [("enqueue", "a", 3), ("enqueue", "b", 2), ("cancel", "b", 0)],
                        ["a"],
                        ["a"],
                        [],
                    ),
                    (
                        "release",
                        [("enqueue", "a", 3), ("release", "a", 0)],
                        ["a"],
                        [],
                        [],
                    ),
                    (
                        "cancel_head",
                        [
                            ("enqueue", "a", 2),
                            ("enqueue", "b", 2),
                            ("enqueue", "c", 1),
                            ("cancel", "b", 0),
                        ],
                        ["a", "c"],
                        ["a", "c"],
                        [],
                    ),
                    (
                        "fifo",
                        [("enqueue", "a", 2), ("enqueue", "b", 2), ("enqueue", "c", 1)],
                        ["a"],
                        ["a"],
                        ["b", "c"],
                    ),
                    (
                        "drain",
                        [
                            ("enqueue", "a", 3),
                            ("enqueue", "b", 2),
                            ("enqueue", "c", 1),
                            ("release", "a", 0),
                        ],
                        ["a", "b", "c"],
                        ["b", "c"],
                        [],
                    ),
                    ("unknown", [("cancel", "x", 0), ("release", "x", 0)], [], [], []),
                    (
                        "cancel_tail",
                        [
                            ("enqueue", "a", 3),
                            ("enqueue", "b", 2),
                            ("enqueue", "c", 1),
                            ("cancel", "c", 0),
                        ],
                        ["a"],
                        ["a"],
                        ["b"],
                    ),
                    (
                        "cancel_active",
                        [("enqueue", "a", 1), ("cancel", "a", 0)],
                        ["a"],
                        ["a"],
                        [],
                    ),
                ]
            ]
        ),
        ("production-log",),
        difficulty="medium",
        difficulty_reason="Reconcile FIFO fairness, weighted capacity and cancellation before waking waiters.",
    )

    yield simple(
        "R19",
        "Shutdown discards requests that were already accepted",
        "graceful_service_drain",
        "Process start(id), finish(id) and shutdown events. Initially open; starts accepted only while open. "
        "shutdown moves to draining if requests are active, otherwise closed. Existing requests may finish "
        "while draining; the last finish closes. Repeated shutdown and unknown finishes are harmless. "
        "ids on start are unique. Return accepted start ids, completed ids, sorted active ids and state.",
        """
        def run(request):
            state, active, accepted, completed = "open", set(), [], []
            for event in request["events"]:
                kind = event["op"]
                if kind == "start" and state == "open":
                    active.add(event["id"])
                    accepted.append(event["id"])
                elif kind == "finish" and event["id"] in active:
                    active.remove(event["id"])
                    completed.append(event["id"])
                    if state == "draining" and not active:
                        state = "closed"
                elif kind == "shutdown":
                    state = "draining" if active else "closed"
            return dict(accepted=accepted, completed=completed, active=sorted(active), state=state)
        """,
        (
            'elif kind == "finish" and event["id"] in active:',
            'elif kind == "finish" and state == "open" and event["id"] in active:',
        ),
        {
            "accepts_while_draining": ('state == "open":', 'state != "closed":'),
            "never_closes_drain": (
                'state = "closed"\n        elif',
                'state = "draining"\n        elif',
            ),
        },
        examples(
            [
                (
                    n,
                    {
                        "events": [
                            dict(op=o, **({"id": k} if k else {})) for o, k in events
                        ]
                    },
                    dict(accepted=a, completed=c, active=active, state=s),
                )
                for n, events, a, c, active, s in [
                    ("empty", [], [], [], [], "open"),
                    (
                        "normal",
                        [("start", "a"), ("finish", "a")],
                        ["a"],
                        ["a"],
                        [],
                        "open",
                    ),
                    (
                        "drain",
                        [("start", "a"), ("shutdown", None), ("finish", "a")],
                        ["a"],
                        ["a"],
                        [],
                        "closed",
                    ),
                    ("idle_shutdown", [("shutdown", None)], [], [], [], "closed"),
                    (
                        "reject_new",
                        [("start", "a"), ("shutdown", None), ("start", "b")],
                        ["a"],
                        [],
                        ["a"],
                        "draining",
                    ),
                    (
                        "partial",
                        [
                            ("start", "a"),
                            ("start", "b"),
                            ("shutdown", None),
                            ("finish", "a"),
                        ],
                        ["a", "b"],
                        ["a"],
                        ["b"],
                        "draining",
                    ),
                    (
                        "repeat",
                        [
                            ("start", "a"),
                            ("shutdown", None),
                            ("shutdown", None),
                            ("finish", "a"),
                        ],
                        ["a"],
                        ["a"],
                        [],
                        "closed",
                    ),
                    ("unknown", [("finish", "x")], [], [], [], "open"),
                    (
                        "closed_start",
                        [("shutdown", None), ("start", "a")],
                        [],
                        [],
                        [],
                        "closed",
                    ),
                    (
                        "reverse_finish",
                        [
                            ("start", "a"),
                            ("start", "b"),
                            ("shutdown", None),
                            ("finish", "b"),
                            ("finish", "a"),
                        ],
                        ["a", "b"],
                        ["b", "a"],
                        [],
                        "closed",
                    ),
                ]
            ]
        ),
        ("nist-sms",),
        difficulty="medium",
        difficulty_reason="Separate admission shutdown from completion of already-owned work.",
    )
