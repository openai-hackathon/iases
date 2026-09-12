"""Revised reliability tasks with scoped lifecycle and durable replay interactions.

Primary context: Python asyncio cancellation semantics, OPC UA session/request
identity, and the transactional outbox pattern. All workloads are synthetic.
"""

from .schema import Case, Change, Task, code


def tasks():
    yield singleflight_task()
    yield idempotency_task()
    yield outbox_task()


def singleflight_task():
    files = {
        "fabops/registry.py": code('''
            """Track producer ownership across independently invalidated scopes."""
            import asyncio

            class Registry:
                def __init__(self):
                    self.generations = {}
                    self.entries = {}
                    self.tasks = set()

                def identity(self, scope, key):
                    return (scope, key, self.generations.get(scope, 0))

                def invalidate(self, scope):
                    self.generations[scope] = self.generations.get(scope, 0) + 1

                def retire(self, identity, entry):
                    if self.entries.get(identity) is entry:
                        self.entries.pop(identity, None)

                def acquire(self, scope, key, loader):
                    identity = self.identity(scope, key)
                    entry = self.entries.get(identity)
                    if entry is None or entry["task"].done():
                        task = asyncio.create_task(loader(scope, key, identity[2]))
                        entry = {"task": task, "waiters": 0}
                        self.entries[identity] = entry
                        self.tasks.add(task)
                        def done(task):
                            self.retire(identity, entry)
                            self.tasks.discard(task)
                            if not task.cancelled():
                                task.exception()
                        task.add_done_callback(done)
                    entry["waiters"] += 1
                    return identity, entry

                def release(self, identity, entry):
                    entry["waiters"] -= 1
                    if entry["waiters"] == 0:
                        self.retire(identity, entry)
                        if not entry["task"].done():
                            entry["task"].cancel()
        '''),
        "fabops/flight.py": code('''
            """One caller's cancellation does not own a shared producer."""
            import asyncio
            from .registry import Registry

            class SingleFlight:
                def __init__(self):
                    self.registry = Registry()

                def invalidate(self, scope):
                    self.registry.invalidate(scope)

                async def get(self, scope, key, loader):
                    identity, entry = self.registry.acquire(scope, key, loader)
                    try:
                        return await asyncio.shield(entry["task"])
                    finally:
                        self.registry.release(identity, entry)
        '''),
        "fabops/domain.py": code("""
            import asyncio
            from .flight import SingleFlight

            async def exercise(request):
                flight = SingleFlight()
                gates, answers, waiters, calls, cancellations = {}, {}, {}, [], []
                async def settle():
                    for _ in range(8):
                        await asyncio.sleep(0)
                for command in request["commands"]:
                    op = command["op"]
                    if op == "join":
                        job = command["job"]
                        gates.setdefault(job, asyncio.Event())
                        async def loader(scope, key, generation, job=job, resistant=command.get("resistant", False)):
                            calls.append([job, scope, key, generation])
                            try:
                                await gates[job].wait()
                            except asyncio.CancelledError:
                                cancellations.append(job)
                                if not resistant:
                                    raise
                                await gates[job].wait()
                            answer = answers[job]
                            if answer.get("error"):
                                raise ValueError(answer["error"])
                            return answer.get("value")
                        waiters[command["waiter"]] = asyncio.create_task(
                            flight.get(command["scope"], command["key"], loader))
                    elif op == "cancel":
                        waiters[command["waiter"]].cancel()
                    elif op == "invalidate":
                        flight.invalidate(command["scope"])
                    else:
                        answers[command["job"]] = command
                        gates.setdefault(command["job"], asyncio.Event()).set()
                    await settle()
                results = {}
                for name, waiter in waiters.items():
                    if waiter.cancelled():
                        results[name] = {"status": "cancelled"}
                    elif not waiter.done():
                        results[name] = {"status": "pending"}
                    elif waiter.exception() is not None:
                        results[name] = {"status": "error", "error": str(waiter.exception())}
                    else:
                        results[name] = {"status": "value", "value": waiter.result()}
                active = len(flight.registry.entries)
                for job, gate in gates.items():
                    answers.setdefault(job, {"value": None})
                    gate.set()
                await settle()
                for waiter in waiters.values():
                    if not waiter.done():
                        waiter.cancel()
                await asyncio.gather(*waiters.values(), return_exceptions=True)
                await asyncio.gather(*list(flight.registry.tasks), return_exceptions=True)
                return dict(results=results, calls=calls, cancellations=cancellations, active=active)

            def run(request):
                return asyncio.run(exercise(request))
        """),
    }
    faults = (
        Change(
            "fabops/registry.py",
            "return (scope, key, self.generations.get(scope, 0))",
            'return ("shared", key, 0)',
        ),
        Change(
            "fabops/flight.py",
            'return await asyncio.shield(entry["task"])',
            'return await entry["task"]',
        ),
        Change(
            "fabops/registry.py",
            "if self.entries.get(identity) is entry:",
            "if identity in self.entries:",
        ),
        Change(
            "fabops/registry.py",
            'if entry["waiters"] == 0:',
            'if entry["waiters"] == 0 and entry["task"].done():',
        ),
    )
    mutants = {
        name: (fault,)
        for name, fault in zip(
            (
                "unscoped_generations",
                "unshielded_waiter",
                "stale_retirement",
                "orphan_producer",
            ),
            faults,
        )
    }
    mutants["generation_ignored"] = (
        Change(
            "fabops/registry.py",
            "return (scope, key, self.generations.get(scope, 0))",
            "return (scope, key, 0)",
        ),
    )
    mutants["scope_ignored"] = (
        Change(
            "fabops/registry.py",
            "return (scope, key, self.generations.get(scope, 0))",
            'return ("shared", key, self.generations.get(scope, 0))',
        ),
    )
    return Task(
        "R13",
        "Scoped telemetry requests retain abandoned producers and retire newer work",
        "medium",
        "scoped_generation_singleflight_lifecycle",
        code("""
            Repair the real asyncio SingleFlight.get(scope,key,loader) service. scope and key are
            strings. Share exactly one running producer among callers with the same scope, key and
            current scope generation (initially zero). The producer calls loader(scope,key,generation).
            invalidate(scope) increments only that scope's generation. Existing waiters remain attached
            to their old producer; later callers must use a fresh generation. Completed and failed
            producers are not cached. One waiter cancellation must not cancel other waiters. When the
            last waiter departs, immediately detach its entry and cancel its producer. A producer may
            suppress cancellation and finish later; its retirement must not remove a replacement entry
            for the same identity. Keep live producer tasks referenced and retrieve their exceptions.

            run executes a deterministic command sequence with Event-controlled loaders. join has
            unique waiter and job labels, scope, key, and optional resistant boolean. Each join offers
            its job loader, but a joining follower never starts that loader. cancel names a waiter;
            completed waiters are unaffected. invalidate names a scope. finish(job,value) releases a
            job; finish(job,error=string) instead makes it raise ValueError. Finishing an unstarted job
            is harmless. Commands settle runnable callbacks before the next command, with no positive
            wall-clock sleeps. At the end return results keyed by waiter: {status:value,value:...},
            {status:error,error:...}, {status:cancelled}, or {status:pending}; calls lists actually
            started [job,scope,key,generation] in start order; cancellations lists producer jobs that
            received cancellation; active is the number of registry entries before final cleanup.
            Pending is allowed. Cleanup must finish without leaking tasks. There are at most 30
            commands and eight simultaneous waiters. Preserve the input and the async public API.
        """),
        files,
        faults,
        mutants,
        tuple(singleflight_cases()),
        ("nist-sms",),
        extra_hidden_tests=SINGLEFLIGHT_DIRECT,
        difficulty_reason="Coordinate scoped invalidation, shared caller cancellation, orphan producers and stale asynchronous cleanup through producer identity ownership across two modules; replacing shield alone cannot repair lifecycle semantics.",
        version="2.0",
    )


def join(waiter, job, scope="cell", key="sensor", resistant=False):
    return dict(
        op="join", waiter=waiter, job=job, scope=scope, key=key, resistant=resistant
    )


def finish(job, value=None, error=None):
    result = dict(op="finish", job=job)
    result["error" if error else "value"] = error or value
    return result


def singleflight_cases():
    def c(name, commands, results, calls, cancellations=(), active=0, public=False):
        return Case(
            name,
            {"commands": commands},
            dict(
                results=results,
                calls=calls,
                cancellations=list(cancellations),
                active=active,
            ),
            public=public,
        )

    def v(value):
        return {"status": "value", "value": value}

    cancelled, pending = {"status": "cancelled"}, {"status": "pending"}

    def call(job, scope="cell", key="sensor", gen=0):
        return [job, scope, key, gen]

    def cancel(waiter):
        return {"op": "cancel", "waiter": waiter}

    def invalidate(scope="cell"):
        return {"op": "invalidate", "scope": scope}

    yield c(
        "single",
        [join("a", "p"), finish("p", 3)],
        {"a": v(3)},
        [call("p")],
        public=True,
    )
    yield c(
        "scopes_do_not_share",
        [join("a", "p", "x"), join("b", "q", "y"), finish("p", 1), finish("q", 2)],
        {"a": v(1), "b": v(2)},
        [call("p", "x"), call("q", "y")],
        public=True,
    )
    yield c(
        "cancel_one_follower",
        [join("a", "p"), join("b", "q"), cancel("a"), finish("p", 4)],
        {"a": cancelled, "b": v(4)},
        [call("p")],
        public=True,
    )
    yield c(
        "new_generation_runs_independently",
        [join("a", "p"), invalidate(), join("b", "q"), finish("q", 2), finish("p", 1)],
        {"a": v(1), "b": v(2)},
        [call("p"), call("q", gen=1)],
        public=True,
    )
    yield c("empty", [], {}, [])
    yield c(
        "same_identity_shares",
        [join("a", "p"), join("b", "q"), finish("p", 7)],
        {"a": v(7), "b": v(7)},
        [call("p")],
    )
    yield c(
        "distinct_keys",
        [
            join("a", "p", key="a"),
            join("b", "q", key="b"),
            finish("p", 1),
            finish("q", 2),
        ],
        {"a": v(1), "b": v(2)},
        [call("p", key="a"), call("q", key="b")],
    )
    yield c(
        "last_cancel_reclaims",
        [join("a", "p"), cancel("a")],
        {"a": cancelled},
        [call("p")],
        ["p"],
    )
    yield c(
        "all_cancel_then_retry",
        [
            join("a", "p"),
            join("b", "q"),
            cancel("a"),
            cancel("b"),
            join("c", "r"),
            finish("r", 8),
        ],
        {"a": cancelled, "b": cancelled, "c": v(8)},
        [call("p"), call("r")],
        ["p"],
    )
    yield c(
        "failure_not_cached",
        [join("a", "p"), finish("p", error="offline"), join("b", "q"), finish("q", 8)],
        {"a": {"status": "error", "error": "offline"}, "b": v(8)},
        [call("p"), call("q")],
    )
    yield c(
        "success_not_cached",
        [join("a", "p"), finish("p", 1), join("b", "q"), finish("q", 2)],
        {"a": v(1), "b": v(2)},
        [call("p"), call("q")],
    )
    yield c(
        "invalidate_other_scope",
        [join("a", "p", "x"), invalidate("y"), join("b", "q", "x"), finish("p", 4)],
        {"a": v(4), "b": v(4)},
        [call("p", "x")],
    )
    yield c(
        "double_invalidation",
        [invalidate(), invalidate(), join("a", "p"), finish("p", 0)],
        {"a": v(0)},
        [call("p", gen=2)],
    )
    yield c(
        "stale_resistant_completion_cannot_retire_replacement",
        [
            join("a", "p", resistant=True),
            cancel("a"),
            join("b", "q"),
            finish("p", 1),
            join("c", "r"),
            finish("q", 2),
        ],
        {"a": cancelled, "b": v(2), "c": v(2)},
        [call("p"), call("q")],
        ["p"],
    )
    yield c(
        "stale_resistant_failure_cannot_retire_replacement",
        [
            join("a", "p", resistant=True),
            cancel("a"),
            join("b", "q"),
            finish("p", error="stale"),
            join("c", "r"),
            finish("q", 2),
        ],
        {"a": cancelled, "b": v(2), "c": v(2)},
        [call("p"), call("q")],
        ["p"],
    )
    yield c(
        "pending_producer_retained",
        [join("a", "p"), join("b", "q")],
        {"a": pending, "b": pending},
        [call("p")],
        active=1,
    )
    yield c(
        "old_generation_cancel_does_not_touch_new",
        [join("a", "p"), invalidate(), join("b", "q"), cancel("a"), finish("q", 5)],
        {"a": cancelled, "b": v(5)},
        [call("p"), call("q", gen=1)],
        ["p"],
    )
    yield c(
        "cancel_follower_in_new_generation",
        [invalidate(), join("a", "p"), join("b", "q"), cancel("b"), finish("p", 5)],
        {"a": v(5), "b": cancelled},
        [call("p", gen=1)],
    )
    yield c(
        "scope_isolation_with_cancellation",
        [join("a", "p", "x"), join("b", "q", "y"), cancel("a"), finish("q", 6)],
        {"a": cancelled, "b": v(6)},
        [call("p", "x"), call("q", "y")],
        ["p"],
    )
    yield c(
        "invalidate_preserves_old_waiter",
        [join("a", "p"), invalidate(), finish("p", 9)],
        {"a": v(9)},
        [call("p")],
    )


def idempotency_task():
    files = {
        "fabops/canonical.py": code('''
            """Typed command identities exclude transport metadata."""
            import json
            from decimal import Decimal

            def normalize(value):
                if value is None:
                    return ["null"]
                if isinstance(value, bool):
                    return ["bool", value]
                if isinstance(value, (int, float)):
                    number = Decimal(str(value))
                    sign, digits, exponent = number.as_tuple()
                    digits = list(digits)
                    if not any(digits):
                        return ["number", 0, [0], 0]
                    while digits[-1] == 0:
                        digits.pop()
                        exponent += 1
                    return ["number", sign, digits, exponent]
                if isinstance(value, str):
                    return ["string", value]
                if isinstance(value, list):
                    return ["array", [normalize(item) for item in value]]
                return ["object", [[key, normalize(value[key])] for key in sorted(value)]]

            def fingerprint(command):
                return json.dumps(normalize([command["expected"], command["value"]]), separators=(",", ":"))

            def scope_key(scope):
                return json.dumps(scope, separators=(",", ":"))
        '''),
        "fabops/commands.py": code('''
            """The state revision and cached command outcome share one commit."""
            import json
            import sqlite3
            from .canonical import fingerprint, scope_key

            def connect(path):
                db = sqlite3.connect(path)
                db.executescript("""
                    CREATE TABLE IF NOT EXISTS states(scope TEXT PRIMARY KEY, revision INTEGER, value TEXT);
                    CREATE TABLE IF NOT EXISTS receipts(scope TEXT, key TEXT, fingerprint TEXT, reply TEXT,
                        PRIMARY KEY(scope,key));
                """)
                return db

            def execute(db, command):
                scope, key = scope_key(command["scope"]), command["key"]
                identity = fingerprint(command)
                previous = db.execute("SELECT fingerprint,reply FROM receipts WHERE scope=? AND key=?", (scope,key)).fetchone()
                if previous:
                    return json.loads(previous[1]) if previous[0] == identity else {"status": "conflict"}
                db.execute("BEGIN IMMEDIATE")
                try:
                    current = db.execute("SELECT revision,value FROM states WHERE scope=?", (scope,)).fetchone()
                    revision, value = (current[0],json.loads(current[1])) if current else (0,None)
                    if command["expected"] != revision:
                        reply = dict(status="precondition", revision=revision, value=value)
                    else:
                        revision += 1
                        value = command["value"]
                        db.execute("INSERT OR REPLACE INTO states VALUES (?,?,?)", (scope,revision,json.dumps(value)))
                        reply = dict(status="applied", revision=revision, value=value)
                    if command.get("crash", False):
                        raise RuntimeError("interrupted command")
                    db.execute("INSERT INTO receipts VALUES (?,?,?,?)", (scope,key,identity,json.dumps(reply)))
                    db.commit()
                    return reply
                except RuntimeError:
                    db.rollback()
                    return {"status": "crashed"}
        '''),
        "fabops/domain.py": code("""
            import json
            import tempfile
            from pathlib import Path
            from .commands import connect, execute
            def run(request):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "commands.sqlite"
                    db = connect(path)
                    results = []
                    try:
                        for command in request["commands"]:
                            if command["op"] == "restart":
                                db.close()
                                db = connect(path)
                                results.append({"status": "restarted"})
                            else:
                                results.append(execute(db, command))
                        states = [[json.loads(scope), revision, json.loads(value)]
                                  for scope, revision, value in db.execute("SELECT * FROM states")]
                        states.sort(key=lambda row: row[0])
                        return dict(results=results, states=states,
                                    receipts=db.execute("SELECT COUNT(*) FROM receipts").fetchone()[0])
                    finally:
                        db.close()
        """),
    }
    faults = (
        Change(
            "fabops/commands.py",
            'WHERE scope=? AND key=?", (scope,key)).fetchone()',
            'WHERE key=?", (key,)).fetchone()',
        ),
        Change(
            "fabops/canonical.py",
            'return json.dumps(normalize([command["expected"], command["value"]]), separators=(",", ":"))',
            'return json.dumps(command["value"], separators=(",", ":"))',
        ),
        Change(
            "fabops/commands.py",
            'if command.get("crash", False):',
            'db.commit()\n        if command.get("crash", False):',
        ),
        Change(
            "fabops/commands.py",
            'db.execute("INSERT INTO receipts VALUES (?,?,?,?)", (scope,key,identity,json.dumps(reply)))',
            'if reply["status"] == "applied":\n            db.execute("INSERT INTO receipts VALUES (?,?,?,?)", (scope,key,identity,json.dumps(reply)))',
        ),
    )
    mutants = {
        name: (fault,)
        for name, fault in zip(
            (
                "cell_without_plant",
                "payload_only_identity",
                "state_before_receipt",
                "drops_rejected_receipt",
            ),
            faults,
        )
    }
    mutants["bool_is_number"] = (
        Change(
            "fabops/canonical.py",
            'return ["bool", value]',
            "return normalize(int(value))",
        ),
    )
    mutants["sorts_arrays"] = (
        Change(
            "fabops/canonical.py",
            "[normalize(item) for item in value]",
            "sorted([normalize(item) for item in value], key=repr)",
        ),
    )
    return Task(
        "R21",
        "Scoped recipe commands replay the wrong revision and lose rejected outcomes",
        "medium",
        "scoped_revision_idempotency_transaction",
        code("""
            Process commands against a real SQLite file. A command has op=execute, scope=[plant,cell]
            (two strings), opaque key, expected nonnegative integer revision, arbitrary finite JSON
            value, optional transport metadata, and optional crash boolean. Each scope initially has
            revision zero and value null. The idempotency namespace is the complete scope plus key.
            For a previously unseen key, compare expected with the current scope revision: equality
            applies value and increments the revision, returning {status:applied,revision,value};
            mismatch returns {status:precondition,revision,value} with the unchanged current state.
            Cache BOTH outcomes. Repeating a key with the same expected revision and equivalent value
            returns the original outcome, regardless of subsequent state changes. Reusing that key
            with a different expected revision or nonequivalent value returns {status:conflict} and
            changes nothing. Transport metadata and crash flags are not part of semantic identity.

            Values are equivalent recursively: object key order is irrelevant; array order is
            significant; finite numbers compare by decimal value (1 equals 1.0, negative zero equals
            zero); booleans are distinct from numbers; strings retain exact content; null is distinct
            from every other value. Keys inside objects are strings; no NaN or infinity occurs.
            Preserve the first accepted value's original representation in cached replies. A crash
            on a previously unseen command happens after computing/updating state but before recording
            the outcome; return {status:crashed}, with neither state nor receipt surviving. A retry of
            an already cached command does not enter that crash point. restart closes and reopens the
            same SQLite file and returns {status:restarted}. Return results in command order, states
            as sorted [[plant,cell],revision,value] rows for scopes that have had successful updates,
            and receipts as the number of cached keys, including precondition failures. Failed
            preconditions do not create state rows. Bound: at most 30 commands and eight scopes.
        """),
        files,
        faults,
        mutants,
        tuple(idempotency_cases()),
        ("nist-sms",),
        difficulty_reason="Combine recursive typed value equivalence, full scope identity, revision-sensitive replay and atomic caching of both positive and negative outcomes across a real database reopen.",
        version="2.0",
    )


def command(key="k", expected=0, value=1, scope=("fab", "cell"), **kwargs):
    return dict(
        op="execute",
        key=key,
        expected=expected,
        value=value,
        scope=list(scope),
        **kwargs,
    )


def idempotency_cases():
    def c(name, commands, results, states=(), receipts=0, public=False):
        return Case(
            name,
            {"commands": commands},
            dict(results=results, states=list(states), receipts=receipts),
            public=public,
        )

    def applied(rev, value):
        return dict(status="applied", revision=rev, value=value)

    def pre(rev, value):
        return dict(status="precondition", revision=rev, value=value)

    def state(rev, value, scope=("fab", "cell")):
        return [list(scope), rev, value]

    conflict, crash, restart = (
        {"status": "conflict"},
        {"status": "crashed"},
        {"op": "restart"},
    )
    restarted = {"status": "restarted"}
    yield c("first_command", [command()], [applied(1, 1)], [state(1, 1)], 1, True)
    yield c(
        "scope_separates_plants",
        [command(scope=("a", "cell")), command(value=2, scope=("b", "cell"))],
        [applied(1, 1), applied(1, 2)],
        [state(1, 1, ("a", "cell")), state(1, 2, ("b", "cell"))],
        2,
        True,
    )
    yield c(
        "object_order_and_numeric_equivalence",
        [
            command(value={"a": 1, "b": [2, 3]}),
            command(value={"b": [2.0, 3], "a": 1.0}),
        ],
        [applied(1, {"a": 1, "b": [2, 3]})] * 2,
        [state(1, {"a": 1, "b": [2, 3]})],
        1,
        True,
    )
    yield c(
        "crash_then_retry",
        [command(crash=True), restart, command()],
        [crash, restarted, applied(1, 1)],
        [state(1, 1)],
        1,
        True,
    )
    yield c("empty", [], [])
    yield c(
        "duplicate_after_restart",
        [command(), restart, command(trace_id="new")],
        [applied(1, 1), restarted, applied(1, 1)],
        [state(1, 1)],
        1,
    )
    yield c(
        "revision_is_part_of_identity",
        [command(), command(expected=1)],
        [applied(1, 1), conflict],
        [state(1, 1)],
        1,
    )
    yield c(
        "changed_value_conflicts",
        [command(), command(value=2)],
        [applied(1, 1), conflict],
        [state(1, 1)],
        1,
    )
    yield c(
        "boolean_not_numeric",
        [command(value=True), command(value=1)],
        [applied(1, True), conflict],
        [state(1, True)],
        1,
    )
    yield c(
        "array_order_significant",
        [command(value=[1, 2]), command(value=[2, 1])],
        [applied(1, [1, 2]), conflict],
        [state(1, [1, 2])],
        1,
    )
    yield c(
        "negative_zero_equivalence",
        [command(value=-0.0), command(value=0)],
        [applied(1, -0.0)] * 2,
        [state(1, -0.0)],
        1,
    )
    yield c(
        "stale_result_is_cached",
        [command("bad", 3), command("good", 0, 2), command("bad", 3)],
        [pre(0, None), applied(1, 2), pre(0, None)],
        [state(1, 2)],
        2,
    )
    yield c(
        "rejected_receipt_survives_restart",
        [command(expected=2), restart, command(expected=2)],
        [pre(0, None), restarted, pre(0, None)],
        [],
        1,
    )
    yield c(
        "duplicate_reply_not_current_state",
        [command(), command("next", 1, 2), command()],
        [applied(1, 1), applied(2, 2), applied(1, 1)],
        [state(2, 2)],
        2,
    )
    yield c(
        "nested_type_boundary",
        [command(value={"x": [False, None]}), command(value={"x": [0, None]})],
        [applied(1, {"x": [False, None]}), conflict],
        [state(1, {"x": [False, None]})],
        1,
    )
    yield c(
        "nested_array_permutation",
        [
            command(value={"x": [{"a": 1}, {"b": 2}]}),
            command(value={"x": [{"b": 2}, {"a": 1}]}),
        ],
        [applied(1, {"x": [{"a": 1}, {"b": 2}]}), conflict],
        [state(1, {"x": [{"a": 1}, {"b": 2}]})],
        1,
    )
    yield c(
        "scoped_same_key_after_restart",
        [
            command(scope=("a", "c")),
            restart,
            command(value=7, scope=("b", "c")),
            command(scope=("a", "c")),
        ],
        [applied(1, 1), restarted, applied(1, 7), applied(1, 1)],
        [state(1, 1, ("a", "c")), state(1, 7, ("b", "c"))],
        2,
    )
    yield c(
        "crash_restores_existing_state",
        [command(), command("next", 1, 5, crash=True), restart, command("next", 1, 5)],
        [applied(1, 1), crash, restarted, applied(2, 5)],
        [state(2, 5)],
        2,
    )
    yield c(
        "cached_retry_ignores_crash",
        [command(), command(crash=True)],
        [applied(1, 1)] * 2,
        [state(1, 1)],
        1,
    )
    yield c(
        "numeric_representation_inside_objects",
        [command(value={"z": 1000, "a": None}), command(value={"a": None, "z": 1e3})],
        [applied(1, {"z": 1000, "a": None})] * 2,
        [state(1, {"z": 1000, "a": None})],
        1,
    )

    huge = 1234567890123456789012345678901
    yield c(
        "large_integer_identity_remains_exact",
        [command(value=huge), command(value=huge + 1)],
        [applied(1, huge), conflict],
        [state(1, huge)],
        1,
    )
    yield c(
        "integer_exponent_equivalence",
        [command(value=10**30), command(value=1e30)],
        [applied(1, 10**30)] * 2,
        [state(1, 10**30)],
        1,
    )


def outbox_task():
    drain = code("""
        def drain(db, consumer):
            next_sequence, total, trail = db.execute(
                "SELECT next,total,trail FROM consumers WHERE id=?", (consumer,)).fetchone()
            trail = json.loads(trail)
            while True:
                item = db.execute("SELECT event,delta FROM inbox WHERE consumer=? AND seq=?",
                                  (consumer,next_sequence)).fetchone()
                if item is None:
                    break
                event, delta = item
                total += delta
                trail.append(event)
                db.execute("DELETE FROM inbox WHERE consumer=? AND seq=?", (consumer,next_sequence))
                next_sequence += 1
            db.execute("UPDATE consumers SET next=?,total=?,trail=? WHERE id=?",
                       (next_sequence,total,json.dumps(trail),consumer))
    """)
    eager_drain = code("""
        def drain(db, consumer):
            next_sequence, total, trail = db.execute(
                "SELECT next,total,trail FROM consumers WHERE id=?", (consumer,)).fetchone()
            trail = json.loads(trail)
            buffered = db.execute("SELECT seq,event,delta FROM inbox WHERE consumer=? ORDER BY seq",
                                  (consumer,)).fetchall()
            for sequence, event, delta in buffered:
                total += delta
                trail.append(event)
                next_sequence = sequence + 1
            db.execute("DELETE FROM inbox WHERE consumer=?", (consumer,))
            db.execute("UPDATE consumers SET next=?,total=?,trail=? WHERE id=?",
                       (next_sequence,total,json.dumps(trail),consumer))
    """)
    safe_cut = code("""
        def safe_cut(db):
            cut, next_sequence = db.execute("SELECT compacted,next FROM source WHERE id=1").fetchone()
            frontier = min(row[0] for row in db.execute("SELECT next FROM consumers"))
            while cut + 1 < min(frontier, next_sequence):
                acknowledged = db.execute("SELECT COUNT(*) FROM acks WHERE seq=?", (cut+1,)).fetchone()[0]
                if acknowledged != 2:
                    break
                cut += 1
            return cut
    """)
    files = {
        "fabops/store.py": code('''
            """Durable source state is independent of compactable delivery payloads."""
            import sqlite3

            def connect(path):
                db = sqlite3.connect(path)
                db.executescript("""
                    CREATE TABLE IF NOT EXISTS source(id INTEGER PRIMARY KEY,next INTEGER,total INTEGER,epoch INTEGER,compacted INTEGER);
                    INSERT OR IGNORE INTO source VALUES(1,1,0,0,0);
                    CREATE TABLE IF NOT EXISTS commands(id TEXT PRIMARY KEY,delta INTEGER,seq INTEGER);
                    CREATE TABLE IF NOT EXISTS outbox(seq INTEGER PRIMARY KEY,event TEXT,delta INTEGER);
                    CREATE TABLE IF NOT EXISTS lease(id INTEGER PRIMARY KEY,owner TEXT,token INTEGER,expires INTEGER);
                    CREATE TABLE IF NOT EXISTS acks(seq INTEGER,consumer TEXT,PRIMARY KEY(seq,consumer));
                    CREATE TABLE IF NOT EXISTS consumers(id TEXT PRIMARY KEY,next INTEGER,total INTEGER,trail TEXT);
                    INSERT OR IGNORE INTO consumers VALUES('mes',1,0,'[]');
                    INSERT OR IGNORE INTO consumers VALUES('quality',1,0,'[]');
                    CREATE TABLE IF NOT EXISTS inbox(consumer TEXT,seq INTEGER,event TEXT,delta INTEGER,PRIMARY KEY(consumer,seq));
                """)
                return db

            def append(db, command):
                previous = db.execute("SELECT delta,seq FROM commands WHERE id=?", (command["id"],)).fetchone()
                if previous:
                    return previous[1] if previous[0] == command["delta"] else "conflict"
                db.execute("BEGIN IMMEDIATE")
                try:
                    sequence = db.execute("SELECT next FROM source WHERE id=1").fetchone()[0]
                    db.execute("UPDATE source SET next=next+1,total=total+? WHERE id=1", (command["delta"],))
                    db.execute("INSERT INTO commands VALUES(?,?,?)", (command["id"],command["delta"],sequence))
                    if command.get("crash", False):
                        raise RuntimeError("interrupted append")
                    db.execute("INSERT INTO outbox VALUES(?,?,?)", (sequence,command["id"],command["delta"]))
                    db.commit()
                    return sequence
                except RuntimeError:
                    db.rollback()
                    return "crashed"
        '''),
        "fabops/lease.py": code('''
            """Grant durable fencing epochs, including after the active lease is retired."""
            def valid(db, command):
                lease = db.execute("SELECT owner,token,expires FROM lease WHERE id=1").fetchone()
                return bool(lease and command["owner"] == lease[0]
                            and command["token"] == lease[1] and command["now"] < lease[2])

            def acquire(db, command):
                lease = db.execute("SELECT expires FROM lease WHERE id=1").fetchone()
                if lease and command["now"] < lease[0]:
                    return None
                with db:
                    token = db.execute("SELECT epoch FROM source WHERE id=1").fetchone()[0] + 1
                    db.execute("UPDATE source SET epoch=? WHERE id=1", (token,))
                    db.execute("INSERT OR REPLACE INTO lease VALUES(1,?,?,?)",
                               (command["owner"],token,command["now"]+command["ttl"]))
                return token
        '''),
        "fabops/consumer.py": '"""Buffer durable gaps and apply exactly one contiguous stream prefix."""\nimport json\n\n'
        + drain
        + code("""
            def accept(db, consumer, sequence, event, delta):
                db.execute("BEGIN IMMEDIATE")
                try:
                    frontier = db.execute("SELECT next FROM consumers WHERE id=?", (consumer,)).fetchone()[0]
                    if sequence >= frontier:
                        db.execute("INSERT OR IGNORE INTO inbox VALUES(?,?,?,?)", (consumer,sequence,event,delta))
                    drain(db, consumer)
                    db.commit()
                except Exception:
                    db.rollback()
                    raise
        """),
        "fabops/relay.py": code('''
            """A sink commit cannot be rolled back by a missing local acknowledgement."""
            from .consumer import accept
            from .lease import valid

            def deliver(db, command):
                if not valid(db, command):
                    return "fenced"
                sequence, consumer = command["seq"], command["consumer"]
                event = db.execute("SELECT event,delta FROM outbox WHERE seq=?", (sequence,)).fetchone()
                if event is None:
                    return "missing"
                if db.execute("SELECT 1 FROM acks WHERE seq=? AND consumer=?", (sequence,consumer)).fetchone():
                    return "acked"
                if command.get("crash") == "before_sink":
                    return "crashed"
                accept(db, consumer, sequence, *event)
                if command.get("crash") == "after_sink":
                    return "crashed"
                with db:
                    db.execute("INSERT OR IGNORE INTO acks VALUES(?,?)", (sequence,consumer))
                return "acked"
        '''),
        "fabops/retention.py": '"""Compact only a fully consumed and locally acknowledged prefix."""\nfrom .lease import valid\n\n'
        + safe_cut
        + code("""
            def compact(db, command):
                if not valid(db, command):
                    return "fenced"
                db.execute("BEGIN IMMEDIATE")
                try:
                    cut = safe_cut(db)
                    db.execute("DELETE FROM outbox WHERE seq<=?", (cut,))
                    db.execute("DELETE FROM acks WHERE seq<=?", (cut,))
                    db.execute("UPDATE source SET compacted=? WHERE id=1", (cut,))
                    if command.get("crash", False):
                        raise RuntimeError("interrupted compaction")
                    db.commit()
                    return cut
                except RuntimeError:
                    db.rollback()
                    return "crashed"
        """),
        "fabops/domain.py": code("""
            import json
            import tempfile
            from pathlib import Path
            from .store import connect, append
            from .lease import acquire, valid
            from .relay import deliver
            from .retention import compact

            def run(request):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "outbox.sqlite"
                    db = connect(path)
                    results = []
                    try:
                        for command in request["commands"]:
                            op = command["op"]
                            if op == "append":
                                result = append(db, command)
                            elif op == "acquire":
                                result = acquire(db, command)
                            elif op == "deliver":
                                result = deliver(db, command)
                            elif op == "compact":
                                result = compact(db, command)
                            elif op == "retire":
                                result = "fenced"
                                if valid(db, command):
                                    with db:
                                        db.execute("DELETE FROM lease")
                                    result = "retired"
                            else:
                                db.close()
                                db = connect(path)
                                result = "restarted"
                            results.append(result)
                        next_sequence,total,epoch,cut = db.execute("SELECT next,total,epoch,compacted FROM source WHERE id=1").fetchone()
                        lease = db.execute("SELECT owner,token,expires FROM lease WHERE id=1").fetchone()
                        consumers = {}
                        for name,frontier,value,trail in db.execute("SELECT * FROM consumers"):
                            consumers[name] = dict(next=frontier,total=value,trail=json.loads(trail),
                                buffered=[row[0] for row in db.execute("SELECT seq FROM inbox WHERE consumer=? ORDER BY seq", (name,))])
                        return dict(results=results,next_sequence=next_sequence,total=total,epoch=epoch,compacted=cut,
                                    lease=list(lease) if lease else None,consumers=consumers,
                                    retained=[row[0] for row in db.execute("SELECT seq FROM outbox ORDER BY seq")],
                                    acks=[list(row) for row in db.execute("SELECT seq,consumer FROM acks ORDER BY seq,consumer")],
                                    commands=db.execute("SELECT COUNT(*) FROM commands").fetchone()[0])
                    finally:
                        db.close()
        """),
    }
    faults = (
        Change(
            "fabops/store.py",
            'if command.get("crash", False):',
            'db.commit()\n        if command.get("crash", False):',
        ),
        Change("fabops/consumer.py", drain, eager_drain),
        Change(
            "fabops/relay.py",
            'if command.get("crash") == "before_sink":',
            'with db:\n        db.execute("INSERT OR IGNORE INTO acks VALUES(?,?)", (sequence,consumer))\n    if command.get("crash") == "before_sink":',
        ),
        Change(
            "fabops/retention.py",
            safe_cut,
            code("""
            def safe_cut(db):
                return max(row[0] for row in db.execute("SELECT next FROM consumers")) - 1
        """),
        ),
        Change(
            "fabops/lease.py",
            'and command["token"] == lease[1] and command["now"] < lease[2]',
            'and command["now"] < lease[2]',
        ),
    )
    mutants = {
        name: (fault,)
        for name, fault in zip(
            (
                "split_source_commit",
                "eager_gap_reducer",
                "ack_before_sink",
                "aggressive_compaction",
                "owner_without_fencing",
            ),
            faults,
        )
    }
    mutants["epoch_from_active_lease"] = (
        Change(
            "fabops/lease.py",
            'db.execute("SELECT epoch FROM source WHERE id=1").fetchone()[0] + 1',
            '(db.execute("SELECT COALESCE(MAX(token),0) FROM lease").fetchone()[0]) + 1',
        ),
    )
    mutants["expiry_is_inclusive"] = (
        Change(
            "fabops/lease.py", 'command["now"] < lease[2]', 'command["now"] <= lease[2]'
        ),
    )
    mutants["compaction_commits_before_crash"] = (
        Change(
            "fabops/retention.py",
            'if command.get("crash", False):',
            'db.commit()\n        if command.get("crash", False):',
        ),
    )
    mutants["compaction_erases_idempotency"] = (
        Change(
            "fabops/retention.py",
            'db.execute("DELETE FROM outbox WHERE seq<=?", (cut,))',
            'db.execute("DELETE FROM outbox WHERE seq<=?", (cut,))\n        db.execute("DELETE FROM commands WHERE seq<=?", (cut,))',
        ),
    )
    mutants["ackless_compaction"] = (
        Change("fabops/retention.py", "if acknowledged != 2:", "if acknowledged < 0:"),
    )
    return Task(
        "R29",
        "Outbox recovery crosses consumer gaps and reclaims unacknowledged fenced work",
        "hard",
        "durable_ordered_outbox_fenced_consumer_compaction",
        code("""
            Implement a durable ordered publication service using the existing SQLite file. Two
            consumers, mes and quality, begin with next=1,total=0,trail=[],buffered=[]. Source begins
            next_sequence=1,total=0,epoch=0,compacted=0. append(id,delta,crash=false) assigns the next
            global sequence, advances it, adds integer delta to source total, remembers the immutable
            id/delta/sequence and records an outbox payload in ONE transaction. An identical id/delta
            retry returns its original sequence even after compaction. A changed delta under an old id
            returns conflict. A crash before the outbox write returns crashed and preserves ALL source
            state. Deltas are integers between -1000 and 1000. Return the assigned sequence for successful append/retry.

            acquire(owner,now,ttl) returns null while a lease is unexpired; otherwise grant a strictly
            increasing durable positive token, with expires=now+ttl. ttl is positive; command times are
            nonnegative, nondecreasing integers at most 1000000, and ttl is at most 10000. retire(owner,token,now) deletes an active matching lease and returns retired;
            otherwise fenced. Retiring never resets the durable epoch. deliver and compact require
            matching owner AND token and now<expires, otherwise return fenced without any effect.

            deliver(seq,consumer,owner,token,now,crash=none) returns missing for an unavailable outbox
            sequence, or acked if already locally acknowledged. Otherwise before_sink crash returns
            crashed with no changes. The sink transaction buffers the event durably and drains ONLY
            its contiguous sequence prefix: for each newly applied event add delta, append its id to
            trail, advance next and remove its buffer row. A duplicate sequence below next does not
            apply again. Out-of-order events remain buffered across restart; no gap may be skipped.
            An after_sink crash commits this consumer state but leaves the local ack absent, returning
            crashed. Normal delivery then commits a separate (sequence,consumer) ack and returns acked,
            including for buffered events. Retry must neither lose the sink effect nor duplicate it.

            compact(owner,token,now,crash=false) reclaims only the largest contiguous prefix beyond
            compacted for which BOTH consumers have applied every event AND BOTH local acks exist.
            Atomically delete outbox/ack rows through that cut and advance compacted, returning the
            cut. Never discard durable command identities, source next_sequence, lease epoch, consumer
            totals/trails or gap buffers. A compaction crash after its SQL deletes but before commit
            returns crashed and preserves the former durable state. A valid call with no eligible
            prefix returns the unchanged cut. restart closes/reopens the same file and returns restarted.

            Return per-command results; source next_sequence,total,epoch,compacted; active lease as
            [owner,token,expires] or null; consumers with next,total,trail and sorted buffered sequences;
            sorted retained outbox sequences; sorted [sequence,consumer] acks; and commands count.
            Total/trail/next are observable durable consumer state, not recomputed from retained outbox
            rows. Every sink application and local ack are separate real SQLite commits; actual disk
            reopen and rollback matter. There are at most 50 commands, 12 appended ids, and two consumers.
        """),
        files,
        faults,
        mutants,
        tuple(outbox_cases()),
        ("nist-sms",),
        difficulty_reason="Replace an eager out-of-order reducer and unsafe retention architecture while coordinating independently committed sink effects, local acknowledgements, durable producer identities, epoch fencing and crash-safe compaction across six modules.",
        version="2.0",
    )


def outbox_cases():
    def a(identifier="e1", delta=5, crash=False):
        return dict(op="append", id=identifier, delta=delta, crash=crash)

    def lease_grant(owner="w", now=0, ttl=100):
        return dict(op="acquire", owner=owner, now=now, ttl=ttl)

    def d(seq=1, consumer="mes", owner="w", token=1, now=0, crash="none"):
        return dict(
            op="deliver",
            seq=seq,
            consumer=consumer,
            owner=owner,
            token=token,
            now=now,
            crash=crash,
        )

    def compact(owner="w", token=1, now=0, crash=False):
        return dict(op="compact", owner=owner, token=token, now=now, crash=crash)

    def retire(owner="w", token=1, now=0):
        return dict(op="retire", owner=owner, token=token, now=now)

    def consumer(next=1, total=0, trail=(), buffered=()):
        return dict(next=next, total=total, trail=list(trail), buffered=list(buffered))

    def c(
        name,
        commands,
        results,
        *,
        n=2,
        total=5,
        epoch=1,
        cut=0,
        lease=("w", 1, 100),
        mes=None,
        quality=None,
        retained=(1,),
        acks=(),
        count=1,
        public=False,
    ):
        return Case(
            name,
            {"commands": commands},
            dict(
                results=results,
                next_sequence=n,
                total=total,
                epoch=epoch,
                compacted=cut,
                lease=list(lease) if lease else None,
                consumers={"mes": mes or consumer(), "quality": quality or consumer()},
                retained=list(retained),
                acks=[list(pair) for pair in acks],
                commands=count,
            ),
            public=public,
        )

    restart = {"op": "restart"}
    one = consumer(2, 5, ["e1"])
    two = consumer(3, 12, ["e1", "e2"])
    yield c(
        "ordered_two_consumers",
        [a(), lease_grant(), d(), d(consumer="quality")],
        [1, 1, "acked", "acked"],
        mes=one,
        quality=one,
        acks=[(1, "mes"), (1, "quality")],
        public=True,
    )
    yield c(
        "consumer_gap_survives_restart",
        [a(), a("e2", 7), lease_grant(), d(2), restart, d()],
        [1, 2, 1, "acked", "restarted", "acked"],
        n=3,
        total=12,
        mes=two,
        retained=[1, 2],
        acks=[(1, "mes"), (2, "mes")],
        count=2,
        public=True,
    )
    yield c(
        "lost_ack_retries_without_duplicate_effect",
        [a(), lease_grant(), d(crash="after_sink"), restart, d()],
        [1, 1, "crashed", "restarted", "acked"],
        mes=one,
        acks=[(1, "mes")],
        public=True,
    )
    yield c(
        "compaction_waits_for_other_consumer",
        [a(), lease_grant(), d(), compact()],
        [1, 1, "acked", 0],
        mes=one,
        acks=[(1, "mes")],
        public=True,
    )
    yield c("empty", [], [], n=1, total=0, epoch=0, lease=None, retained=[], count=0)
    yield c("append_only", [a()], [1], epoch=0, lease=None)
    yield c(
        "failed_append_has_no_durable_state",
        [a(crash=True), restart],
        ["crashed", "restarted"],
        n=1,
        total=0,
        epoch=0,
        lease=None,
        retained=[],
        count=0,
    )
    yield c(
        "failed_append_retry_uses_sequence_one",
        [a(crash=True), restart, a(), lease_grant(), d()],
        ["crashed", "restarted", 1, 1, "acked"],
        mes=one,
        acks=[(1, "mes")],
    )
    yield c(
        "before_sink_crash_has_no_ack",
        [a(), lease_grant(), d(crash="before_sink"), restart],
        [1, 1, "crashed", "restarted"],
    )
    yield c(
        "before_sink_retry_delivers",
        [a(), lease_grant(), d(crash="before_sink"), restart, d()],
        [1, 1, "crashed", "restarted", "acked"],
        mes=one,
        acks=[(1, "mes")],
    )
    yield c(
        "after_sink_only",
        [a(), lease_grant(), d(crash="after_sink")],
        [1, 1, "crashed"],
        mes=one,
    )
    yield c(
        "gap_buffer_is_observable",
        [a(), a("e2", 7), lease_grant(), d(2)],
        [1, 2, 1, "acked"],
        n=3,
        total=12,
        mes=consumer(buffered=[2]),
        retained=[1, 2],
        acks=[(2, "mes")],
        count=2,
    )
    yield c(
        "two_gaps_drain_in_sequence",
        [a(), a("e2", 7), a("e3", -2), lease_grant(), d(3), d(2), restart, d()],
        [1, 2, 3, 1, "acked", "acked", "restarted", "acked"],
        n=4,
        total=10,
        mes=consumer(4, 10, ["e1", "e2", "e3"]),
        retained=[1, 2, 3],
        acks=[(1, "mes"), (2, "mes"), (3, "mes")],
        count=3,
    )
    yield c(
        "buffered_lost_ack_is_not_double_applied",
        [a(), a("e2", 7), lease_grant(), d(2, crash="after_sink"), d(), restart, d(2)],
        [1, 2, 1, "crashed", "acked", "restarted", "acked"],
        n=3,
        total=12,
        mes=two,
        retained=[1, 2],
        acks=[(1, "mes"), (2, "mes")],
        count=2,
    )
    yield c(
        "acknowledged_retry_is_noop",
        [a(), lease_grant(), d(), d(), restart, d()],
        [1, 1, "acked", "acked", "restarted", "acked"],
        mes=one,
        acks=[(1, "mes")],
    )
    yield c(
        "lease_blocks_concurrent_acquire",
        [a(), lease_grant(), lease_grant("other", 1)],
        [1, 1, None],
    )
    yield c(
        "wrong_owner_fenced", [a(), lease_grant(), d(owner="other")], [1, 1, "fenced"]
    )
    yield c(
        "same_owner_stale_token_fenced",
        [a(), lease_grant(ttl=2), lease_grant(now=2), d(token=1, now=2)],
        [1, 1, 2, "fenced"],
        epoch=2,
        lease=["w", 2, 102],
    )
    yield c(
        "expiry_boundary_fenced",
        [a(), lease_grant(ttl=2), d(now=2)],
        [1, 1, "fenced"],
        lease=["w", 1, 2],
    )
    yield c(
        "retired_epoch_survives_restart",
        [
            a(),
            lease_grant(),
            retire(),
            restart,
            lease_grant(now=1),
            d(token=1, now=1),
            d(token=2, now=1),
        ],
        [1, 1, "retired", "restarted", 2, "fenced", "acked"],
        epoch=2,
        lease=["w", 2, 101],
        mes=one,
        acks=[(1, "mes")],
    )
    yield c(
        "wrong_token_cannot_retire",
        [a(), lease_grant(), retire(token=9), d()],
        [1, 1, "fenced", "acked"],
        mes=one,
        acks=[(1, "mes")],
    )
    yield c(
        "fully_consumed_compaction",
        [a(), lease_grant(), d(), d(consumer="quality"), compact(), restart],
        [1, 1, "acked", "acked", 1, "restarted"],
        cut=1,
        mes=one,
        quality=one,
        retained=[],
    )
    yield c(
        "lost_ack_prevents_compaction",
        [
            a(),
            lease_grant(),
            d(crash="after_sink"),
            d(consumer="quality"),
            compact(),
            restart,
        ],
        [1, 1, "crashed", "acked", 0, "restarted"],
        mes=one,
        quality=one,
        acks=[(1, "quality")],
    )
    yield c(
        "ack_repair_then_compaction",
        [
            a(),
            lease_grant(),
            d(crash="after_sink"),
            d(consumer="quality"),
            compact(),
            d(),
            compact(),
        ],
        [1, 1, "crashed", "acked", 0, "acked", 1],
        cut=1,
        mes=one,
        quality=one,
        retained=[],
    )
    yield c(
        "compaction_crash_rolls_back_payloads_and_cut",
        [a(), lease_grant(), d(), d(consumer="quality"), compact(crash=True), restart],
        [1, 1, "acked", "acked", "crashed", "restarted"],
        mes=one,
        quality=one,
        acks=[(1, "mes"), (1, "quality")],
    )
    yield c(
        "compacted_identity_still_deduplicates",
        [a(), lease_grant(), d(), d(consumer="quality"), compact(), restart, a()],
        [1, 1, "acked", "acked", 1, "restarted", 1],
        cut=1,
        mes=one,
        quality=one,
        retained=[],
    )
    yield c(
        "compacted_identity_rejects_changed_body",
        [a(), lease_grant(), d(), d(consumer="quality"), compact(), a(delta=9)],
        [1, 1, "acked", "acked", 1, "conflict"],
        cut=1,
        mes=one,
        quality=one,
        retained=[],
    )
    yield c(
        "append_after_compaction_preserves_sequence",
        [
            a(),
            lease_grant(),
            d(),
            d(consumer="quality"),
            compact(),
            a("e2", 7),
            d(2),
            d(2, "quality"),
        ],
        [1, 1, "acked", "acked", 1, 2, "acked", "acked"],
        n=3,
        total=12,
        cut=1,
        mes=two,
        quality=two,
        retained=[2],
        acks=[(2, "mes"), (2, "quality")],
        count=2,
    )
    yield c(
        "compact_only_common_applied_prefix",
        [a(), a("e2", 7), lease_grant(), d(), d(2), d(consumer="quality"), compact()],
        [1, 2, 1, "acked", "acked", "acked", 1],
        n=3,
        total=12,
        cut=1,
        mes=two,
        quality=one,
        retained=[2],
        acks=[(2, "mes")],
        count=2,
    )
    yield c(
        "both_acknowledged_gap_still_not_compactable",
        [a(), a("e2", 7), lease_grant(), d(2), d(2, "quality"), compact()],
        [1, 2, 1, "acked", "acked", 0],
        n=3,
        total=12,
        mes=consumer(buffered=[2]),
        quality=consumer(buffered=[2]),
        retained=[1, 2],
        acks=[(2, "mes"), (2, "quality")],
        count=2,
    )
    yield c(
        "stale_worker_cannot_compact",
        [
            a(),
            lease_grant(ttl=1),
            d(),
            d(consumer="quality"),
            lease_grant(now=1),
            compact(token=1, now=1),
        ],
        [1, 1, "acked", "acked", 2, "fenced"],
        epoch=2,
        lease=["w", 2, 101],
        mes=one,
        quality=one,
        acks=[(1, "mes"), (1, "quality")],
    )
    yield c(
        "missing_payload_after_compaction",
        [a(), lease_grant(), d(), d(consumer="quality"), compact(), d()],
        [1, 1, "acked", "acked", 1, "missing"],
        cut=1,
        mes=one,
        quality=one,
        retained=[],
    )
    yield c(
        "lease_after_empty_retirement",
        [lease_grant(), retire(), restart, lease_grant("other", 1)],
        [1, "retired", "restarted", 2],
        n=1,
        total=0,
        epoch=2,
        lease=["other", 2, 101],
        retained=[],
        count=0,
    )


SINGLEFLIGHT_DIRECT = code("""
    def test_direct_generation_owner_handoff():
        import asyncio
        from fabops.flight import SingleFlight
        async def exercise():
            flight = SingleFlight()
            old_started, old_cancelled, old_finish = asyncio.Event(), asyncio.Event(), asyncio.Event()
            new_started, new_finish = asyncio.Event(), asyncio.Event()
            old_done = asyncio.Event()
            calls = []
            async def old_loader(scope, key, generation):
                calls.append((scope,key,generation,"old"))
                old_started.set()
                try:
                    await old_finish.wait()
                except asyncio.CancelledError:
                    old_cancelled.set()
                    await old_finish.wait()
                old_done.set()
                return "old"
            async def new_loader(scope,key,generation):
                calls.append((scope,key,generation,"new"))
                new_started.set()
                await new_finish.wait()
                return "new"
            async def unused_loader(*args):
                raise AssertionError("Replacement follower started another producer")
            try:
                old = asyncio.create_task(flight.get("fab","sensor",old_loader))
                await old_started.wait()
                old.cancel()
                await asyncio.gather(old,return_exceptions=True)
                await old_cancelled.wait()
                current = asyncio.create_task(flight.get("fab","sensor",new_loader))
                await new_started.wait()
                old_finish.set()
                await old_done.wait()
                follower = asyncio.create_task(flight.get("fab","sensor",unused_loader))
                new_finish.set()
                assert await asyncio.gather(current,follower) == ["new","new"]
                assert calls == [("fab","sensor",0,"old"),("fab","sensor",0,"new")]
            finally:
                old_finish.set()
                new_finish.set()

        asyncio.run(asyncio.wait_for(exercise(), timeout=1))

    def test_direct_scope_generation_invalidation():
        import asyncio
        from fabops.flight import SingleFlight
        async def exercise():
            flight = SingleFlight()
            starts = [asyncio.Event(),asyncio.Event()]
            gates = [asyncio.Event(),asyncio.Event()]
            calls = []
            async def loader(scope,key,generation):
                calls.append((scope,key,generation))
                starts[generation].set()
                await gates[generation].wait()
                return generation
            first = asyncio.create_task(flight.get("fab","sensor",loader))
            await starts[0].wait()
            flight.invalidate("fab")
            second = asyncio.create_task(flight.get("fab","sensor",loader))
            await starts[1].wait()
            gates[1].set()
            assert await second == 1
            assert not first.done()
            gates[0].set()
            assert await first == 0
            assert calls == [("fab","sensor",0),("fab","sensor",1)]
        asyncio.run(asyncio.wait_for(exercise(), timeout=1))
""")
