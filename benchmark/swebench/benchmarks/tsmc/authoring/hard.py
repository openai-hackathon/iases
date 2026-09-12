"""Two cross-module repairs: constrained dispatch and durable lease fencing."""

from .easy import examples
from .schema import Change, Task, code


def tasks():
    planner = code('''
        """Enumerate small dispatch plans with shared tool and reticle constraints."""
        def plan(lots, tools, stock):
            lots = sorted(lots, key=lambda lot: lot["id"])
            best, best_score = [], None
            def visit(index, pairs, used, remaining, priority, cost):
                nonlocal best, best_score
                if index == len(lots):
                    score = (-len(pairs), -priority, cost, tuple(pairs))
                    if best_score is None or score < best_score:
                        best, best_score = list(pairs), score
                    return
                lot = lots[index]
                visit(index + 1, pairs, used, remaining, priority, cost)
                reticle = lot["reticle"]
                if remaining.get(reticle, 0) == 0:
                    return
                for tool in sorted(tools):
                    if tool in used or tool not in lot["costs"]:
                        continue
                    next_stock = dict(remaining)
                    next_stock[reticle] -= 1
                    visit(index + 1, pairs + [(lot["id"], tool)], used | {tool}, next_stock,
                          priority + lot["priority"], cost + lot["costs"][tool])
            visit(0, [], set(), dict(stock), 0, 0)
            return [list(pair) for pair in best]
    ''')
    commit = code('''
        """Commit a plan only against the complete observed state revision."""
        def commit_plan(pairs, lots, stock, observed, current):
            if observed != current:
                return False, dict(stock)
            remaining = dict(stock)
            by_id = {lot["id"]: lot for lot in lots}
            for lot, _ in pairs:
                remaining[by_id[lot]["reticle"]] -= 1
            return True, remaining
    ''')
    files = {
        "fabops/planner.py": planner,
        "fabops/store.py": commit,
        "fabops/domain.py": code("""
            from .planner import plan
            from .store import commit_plan
            def run(request):
                pairs = plan(request["lots"], request["tools"], request["stock"])
                accepted, stock = commit_plan(pairs, request["lots"], request["stock"],
                                              request["observed"], request["current"])
                return dict(plan=pairs, committed=accepted, stock=stock)
        """),
    }
    first = Change(
        "fabops/planner.py",
        "(-len(pairs), -priority, cost, tuple(pairs))",
        "(-priority, -len(pairs), cost, tuple(pairs))",
    )
    second = Change(
        "fabops/store.py",
        "if observed != current:",
        'if observed.get("dispatch") != current.get("dispatch"):',
    )
    yield Task(
        "F19",
        "Dispatch optimization and commit disagree about shared resource state",
        "hard",
        "constrained_dispatch_snapshot_commit",
        "Plan and commit dispatch for at most eight lots and four unique tools. Each lot has a unique id, "
        "nonnegative priority, a reticle id, and costs mapping eligible tools to nonnegative setup costs. "
        "Each selected lot needs one tool and one unit of its reticle; tools cannot be shared and reticle "
        "use cannot exceed stock. Optimize lexicographically: maximize selected count, maximize priority "
        "sum, minimize setup cost, then minimize sorted (lot id,tool id) pairs. Return sorted plan pairs. "
        "Commit only if the complete observed revision mapping equals current. On a mismatch, return "
        "committed=false and unchanged stock while retaining the computed plan for diagnostics. Otherwise "
        "deduct selected reticles and return committed=true. Missing reticles have zero capacity. Empty "
        "plans may commit. All revision keys matter; no input object may change.",
        files,
        (first, second),
        {"planner_only": (second,), "snapshot_only": (first,)},
        tuple(dispatch_cases()),
        ("production-log", "nist-sms"),
        difficulty_reason="Solve a non-greedy allocation problem across two shared resources, then enforce an independent complete-snapshot commit invariant in another module.",
    )

    store = code('''
        """Durable epoch allocation separate from the active lease row."""
        import sqlite3
        def connect(path):
            connection = sqlite3.connect(path)
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS epoch (id INTEGER PRIMARY KEY CHECK(id=1), value INTEGER);
                INSERT OR IGNORE INTO epoch VALUES (1, 0);
                CREATE TABLE IF NOT EXISTS lease (id INTEGER PRIMARY KEY CHECK(id=1), owner TEXT, token INTEGER, expires INTEGER);
                CREATE TABLE IF NOT EXISTS output (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT);
                INSERT OR IGNORE INTO output VALUES (1, NULL);
            """)
            return connection
        def allocate(connection):
            token = connection.execute("SELECT value FROM epoch WHERE id=1").fetchone()[0] + 1
            connection.execute("UPDATE epoch SET value=? WHERE id=1", (token,))
            return token
    ''')
    lease = code('''
        """Lease commands and writes share an immediate transaction boundary."""
        from .store import allocate
        def execute(connection, command):
            connection.execute("BEGIN IMMEDIATE")
            try:
                lease = connection.execute("SELECT owner,token,expires FROM lease WHERE id=1").fetchone()
                if command["op"] == "acquire":
                    if lease and command["now"] < lease[2]:
                        result = None
                    else:
                        result = allocate(connection)
                        connection.execute("INSERT OR REPLACE INTO lease VALUES (1,?,?,?)",
                                           (command["owner"], result, command["now"] + command["ttl"]))
                elif command["op"] == "retire":
                    connection.execute("DELETE FROM lease WHERE id=1")
                    result = None
                else:
                    result = bool(lease and command["owner"] == lease[0]
                                  and command["token"] == lease[1] and command["now"] < lease[2])
                    if result:
                        connection.execute("UPDATE output SET value=? WHERE id=1", (command["value"],))
                connection.commit()
                return result
            except Exception:
                connection.rollback()
                raise
    ''')
    files = {
        "fabops/store.py": store,
        "fabops/lease.py": lease,
        "fabops/domain.py": code("""
        import tempfile
        from pathlib import Path
        from .store import connect
        from .lease import execute
        def run(request):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "lease.sqlite"
                connection = connect(path)
                results = []
                try:
                    for command in request["commands"]:
                        if command["op"] == "restart":
                            connection.close()
                            connection = connect(path)
                            results.append(None)
                        else:
                            results.append(execute(connection, command))
                    value = connection.execute("SELECT value FROM output WHERE id=1").fetchone()[0]
                    epoch = connection.execute("SELECT value FROM epoch WHERE id=1").fetchone()[0]
                    return dict(results=results, value=value, epoch=epoch)
                finally:
                    connection.close()
    """),
    }
    first = Change(
        "fabops/store.py",
        'connection.execute("SELECT value FROM epoch WHERE id=1").fetchone()[0] + 1',
        '(connection.execute("SELECT COALESCE(MAX(token),0) FROM lease").fetchone()[0]) + 1',
    )
    second = Change("fabops/lease.py", 'and command["token"] == lease[1] and ', "and ")
    yield Task(
        "R22",
        "Retired lease epochs are reused and stale owners overwrite newer output",
        "hard",
        "durable_fencing_epoch_ownership",
        "Use a real SQLite file to manage a singleton lease and fenced output. acquire(owner,now,ttl) "
        "returns None while a lease is unexpired, otherwise allocates a globally increasing positive "
        "token and expires at now+ttl. Every successful acquisition increments a separately persisted "
        "epoch, even after retire or restart. retire deletes only the lease and returns None; restart "
        "closes and reopens the same database. write(owner,token,now,value) returns true and changes output "
        "only if all three conditions hold: matching owner, matching token, now<expires. Other writes "
        "return false with no side effects. Return per-command results, final output value (initially None) "
        "and epoch (initially 0). Times are nondecreasing, ttl>0, values and owners are strings. "
        "Lease checks and writes must share a SQLite transaction; process memory cannot serve as durability.",
        files,
        (first, second),
        {"epoch_only": (second,), "token_check_only": (first,)},
        tuple(lease_cases()),
        ("nist-sms",),
        difficulty_reason="Repair two interacting invariants across durable epoch allocation, lease deletion, database reopen and transactional stale-writer fencing.",
    )


def dispatch_cases():
    rows = [
        ("empty", [], [], True, {"r": 1, "s": 1}, False),
        ("one", [("a", 1, "r", {"x": 1})], [["a", "x"]], True, {"r": 0, "s": 1}, False),
        (
            "cardinality",
            [("a", 9, "r", {"x": 0}), ("b", 1, "r", {"y": 0}), ("c", 1, "s", {"x": 0})],
            [["b", "y"], ["c", "x"]],
            True,
            {"r": 0, "s": 0},
            False,
        ),
        (
            "no_eligible_tool",
            [("a", 1, "r", {"z": 1})],
            [],
            True,
            {"r": 1, "s": 1},
            False,
        ),
        (
            "stale_inventory",
            [("a", 1, "r", {"x": 1})],
            [["a", "x"]],
            False,
            {"r": 1, "s": 1},
            True,
        ),
        ("stale_empty", [], [], False, {"r": 1, "s": 1}, True),
        (
            "priority",
            [("a", 1, "r", {"x": 0}), ("b", 2, "r", {"x": 1})],
            [["b", "x"]],
            True,
            {"r": 0, "s": 1},
            False,
        ),
        (
            "cost",
            [("a", 1, "r", {"x": 3, "y": 1})],
            [["a", "y"]],
            True,
            {"r": 0, "s": 1},
            False,
        ),
        (
            "tie",
            [("b", 1, "r", {"y": 1}), ("a", 1, "r", {"x": 1})],
            [["a", "x"]],
            True,
            {"r": 0, "s": 1},
            False,
        ),
        (
            "cardinality_reverse",
            [
                ("c", 1, "s", {"x": 0}),
                ("b", 1, "r", {"y": 0}),
                ("a", 99, "r", {"x": 0}),
            ],
            [["b", "y"], ["c", "x"]],
            True,
            {"r": 0, "s": 0},
            False,
        ),
        (
            "missing_stock",
            [("a", 1, "missing", {"x": 0})],
            [],
            True,
            {"r": 1, "s": 1},
            False,
        ),
        (
            "assignment_alternative",
            [("a", 1, "r", {"x": 0, "y": 1}), ("b", 1, "s", {"x": 0})],
            [["a", "y"], ["b", "x"]],
            True,
            {"r": 0, "s": 0},
            False,
        ),
    ]
    return examples(
        [
            (
                n,
                dict(
                    lots=[
                        dict(id=i, priority=p, reticle=r, costs=c)
                        for i, p, r, c in lots
                    ],
                    tools=["x", "y"],
                    stock={"r": 1, "s": 1},
                    observed={"dispatch": 1, "inventory": 1},
                    current={"dispatch": 1, "inventory": 2 if stale else 1},
                ),
                dict(plan=plan, committed=committed, stock=stock),
            )
            for n, lots, plan, committed, stock, stale in rows
        ]
    )


def lease_cases():
    def acquire(owner="a", now=0):
        return dict(op="acquire", owner=owner, now=now, ttl=10)

    def write(owner="a", token=1, now=1, value="ok"):
        return dict(op="write", owner=owner, token=token, now=now, value=value)

    retire, restart = {"op": "retire"}, {"op": "restart"}
    return examples(
        [
            (n, {"commands": commands}, dict(results=results, value=value, epoch=epoch))
            for n, commands, results, value, epoch in [
                ("empty", [], [], None, 0),
                ("first", [acquire(), write()], [1, True], "ok", 1),
                (
                    "retire_reacquire",
                    [acquire(), retire, acquire(now=2)],
                    [1, None, 2],
                    None,
                    2,
                ),
                ("busy", [acquire(), acquire("b", 2)], [1, None], None, 1),
                ("wrong_token", [acquire(), write(token=9)], [1, False], None, 1),
                (
                    "same_owner_stale",
                    [acquire(), retire, acquire(now=2), write(now=3)],
                    [1, None, 2, False],
                    None,
                    2,
                ),
                (
                    "restart_after_retire",
                    [acquire(), retire, restart, acquire(now=2)],
                    [1, None, None, 2],
                    None,
                    2,
                ),
                (
                    "new_owner",
                    [acquire(), acquire("b", 10), write("a", 1, 11)],
                    [1, 2, False],
                    None,
                    2,
                ),
                ("expiry", [acquire(), write(now=10)], [1, False], None, 1),
                (
                    "restart_value",
                    [acquire(), write(), restart, write(token=9, now=2, value="bad")],
                    [1, True, None, False],
                    "ok",
                    1,
                ),
                (
                    "three_epochs",
                    [acquire(), retire, acquire(now=2), retire, acquire(now=4)],
                    [1, None, 2, None, 3],
                    None,
                    3,
                ),
                (
                    "current_token",
                    [acquire(), retire, acquire(now=2), write(token=2, now=3)],
                    [1, None, 2, True],
                    "ok",
                    2,
                ),
            ]
        ]
    )
