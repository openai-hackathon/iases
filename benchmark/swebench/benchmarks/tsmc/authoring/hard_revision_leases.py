"""Atomic resource-set grants and fenced compare-and-swap writes."""

from .schema import Task, Case, Change, code


def tasks():
    files = {
        "fabops/store.py": code('''
            """Persist resource epochs separately from active grants and output versions."""
            import sqlite3

            def connect(path, resources):
                db = sqlite3.connect(path, isolation_level=None)
                db.executescript("""
                    CREATE TABLE IF NOT EXISTS epochs(resource TEXT PRIMARY KEY, value INTEGER);
                    CREATE TABLE IF NOT EXISTS leases(resource TEXT PRIMARY KEY, owner TEXT, token INTEGER, expires INTEGER);
                    CREATE TABLE IF NOT EXISTS outputs(resource TEXT PRIMARY KEY, revision INTEGER, value TEXT);
                """)
                for resource in resources:
                    db.execute("INSERT OR IGNORE INTO epochs VALUES (?,0)", (resource,))
                    db.execute("INSERT OR IGNORE INTO outputs VALUES (?,0,NULL)", (resource,))
                return db

            def allocate(db, resource):
                epoch = db.execute("SELECT value FROM epochs WHERE resource=?", (resource,)).fetchone()[0]+1
                db.execute("UPDATE epochs SET value=? WHERE resource=?", (epoch,resource))
                return epoch

            def snapshot(db):
                return dict(epochs=dict(db.execute("SELECT resource,value FROM epochs ORDER BY resource")),
                            leases={r:[o,t,e] for r,o,t,e in db.execute("SELECT * FROM leases ORDER BY resource")},
                            outputs={r:[rev,value] for r,rev,value in db.execute("SELECT * FROM outputs ORDER BY resource")})
        '''),
        "fabops/fencing.py": code('''
            """Validate the entire ownership and revision read set before any write."""
            def owned(db, owner, tokens, now):
                for resource, token in tokens.items():
                    row = db.execute("SELECT owner,token,expires FROM leases WHERE resource=?", (resource,)).fetchone()
                    if row is None or row[0] != owner or row[1] != token or now >= row[2]:
                        return False
                return True

            def writable(db, command):
                if set(command["tokens"]) != set(command["updates"]) or set(command["expected"]) != set(command["updates"]):
                    return False
                if not owned(db, command["owner"], command["tokens"], command["now"]):
                    return False
                for resource, revision in command["expected"].items():
                    if db.execute("SELECT revision FROM outputs WHERE resource=?", (resource,)).fetchone()[0] != revision:
                        return False
                return True
        '''),
        "fabops/lease.py": code('''
            """One immediate transaction owns a whole grant, renewal, release or write."""
            from .store import allocate
            from .fencing import owned, writable

            def execute(db, command):
                db.execute("BEGIN IMMEDIATE")
                try:
                    op, now = command["op"], command["now"]
                    if op == "acquire":
                        resources = sorted(set(command["resources"]))
                        busy = [db.execute("SELECT expires FROM leases WHERE resource=?", (r,)).fetchone() for r in resources]
                        if any(row and now < row[0] for row in busy):
                            db.rollback()
                            return None
                        result = {}
                        for resource in resources:
                            result[resource] = allocate(db, resource)
                            db.execute("INSERT OR REPLACE INTO leases VALUES (?,?,?,?)",
                                       (resource,command["owner"],result[resource],now+command["ttl"]))
                    elif op in ("renew", "release"):
                        result = owned(db,command["owner"],command["tokens"],now)
                        if not result:
                            db.rollback()
                            return False
                        for resource in command["tokens"]:
                            if op == "renew":
                                db.execute("UPDATE leases SET expires=MAX(expires,?) WHERE resource=?",(now+command["ttl"],resource))
                            else:
                                db.execute("DELETE FROM leases WHERE resource=?",(resource,))
                    else:
                        result = writable(db,command)
                        if not result:
                            db.rollback()
                            return False
                        for resource,value in sorted(command["updates"].items()):
                            db.execute("UPDATE outputs SET revision=revision+1,value=? WHERE resource=?",(value,resource))
                    if command.get("crash",False):
                        raise RuntimeError("interrupted before transaction commit")
                    db.commit()
                    return result
                except RuntimeError:
                    db.rollback()
                    return "crashed"
                except Exception:
                    db.rollback()
                    raise
        '''),
        "fabops/domain.py": code("""
            import tempfile
            from pathlib import Path
            from .store import connect, snapshot
            from .lease import execute

            def run(request):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory)/"grants.sqlite"
                    db = connect(path,request["resources"])
                    results = []
                    try:
                        for command in request["commands"]:
                            if command["op"] == "restart":
                                db.close()
                                db = connect(path,request["resources"])
                                results.append("restarted")
                            elif command["op"] == "read":
                                reader = connect(path,request["resources"])
                                try:
                                    results.append(snapshot(reader))
                                finally:
                                    reader.close()
                            else:
                                results.append(execute(db,command))
                        return dict(results=results,**snapshot(db))
                    finally:
                        db.close()
        """),
    }
    epoch = Change(
        "fabops/store.py",
        'db.execute("SELECT value FROM epochs WHERE resource=?", (resource,)).fetchone()[0]+1',
        '(db.execute("SELECT COALESCE(MAX(token),0) FROM leases WHERE resource=?", (resource,)).fetchone()[0])+1',
    )
    token = Change("fabops/fencing.py", "or row[1] != token ", "")
    preflight = Change(
        "fabops/lease.py",
        "if any(row and now < row[0] for row in busy):",
        "if all(row and now < row[0] for row in busy):",
    )
    scope = Change(
        "fabops/fencing.py",
        'if set(command["tokens"]) != set(command["updates"]) or set(command["expected"]) != set(command["updates"]):',
        "if False:",
    )
    partial = Change(
        "fabops/lease.py",
        'if command.get("crash",False):\n            raise RuntimeError',
        'if command.get("crash",False):\n            db.commit()\n            raise RuntimeError',
    )
    revision = Change(
        "fabops/fencing.py",
        'if db.execute("SELECT revision FROM outputs WHERE resource=?", (resource,)).fetchone()[0] != revision:',
        "if False:",
    )
    faults = (epoch, token, preflight, scope, partial, revision)
    mutants = {
        name: (fault,)
        for name, fault in zip(
            [
                "epoch_from_active_lease",
                "token_not_checked",
                "partial_grant",
                "partial_scope",
                "crash_commits",
                "revision_not_checked",
            ],
            faults,
        )
    }
    mutants["renew_shortens_lease"] = (
        Change("fabops/lease.py", "expires=MAX(expires,?)", "expires=?"),
    )
    mutants["expiry_is_inclusive"] = (
        Change("fabops/fencing.py", "now >= row[2]", "now > row[2]"),
    )
    contract = code("""
        Manage atomic multi-resource leases and fenced versioned outputs in a real SQLite
        file. resources lists 1..4 unique names; initially epochs are 0, no leases exist,
        outputs are [revision=0,value=None]. Resource names in commands always exist.
        Times are nondecreasing integers, ttl>0, owners and values are strings. Sets in
        commands are nonempty; acquire.resources may repeat names and means their set.

        acquire(owner,resources,now,ttl): if ANY requested resource has a lease with
        now<expires, return None with no changes, even to otherwise available resources.
        Otherwise atomically increment EACH resource's independently durable epoch,
        replace all requested leases with [owner,token=epoch,expires=now+ttl], and return
        the resource->token mapping. Expired rows can be replaced. Successful acquisition
        increments every requested epoch, including reacquisition by the same owner;
        release or restart never resets epochs. Unrequested resources are unchanged.

        renew(owner,tokens,now,ttl) and release(owner,tokens,now) require every resource
        to have exactly that owner/token and now<expires. Return False with no effects
        if any check fails. Renewal extends EACH expiry to max(old_expiry,now+ttl)
        without changing tokens; release removes exactly those active leases, preserving
        epochs and outputs. Success returns True. Subsets of an earlier grant are allowed.

        write(owner,tokens,expected,updates,now): tokens, expected and updates must have
        exactly the same resource keys. Require the full live ownership check and all
        expected revisions equal their current output revisions. If any condition fails,
        return False and change nothing. Otherwise write every value, increment every
        output revision by one and return True. Lease validation, revision reads and all
        writes share one immediate transaction; no partial scope or partial write is legal.

        Any modifying command may set crash=true: if validation fails, return its normal
        failure first; otherwise interrupt after SQL changes and before commit, rollback
        EVERYTHING including epoch allocations, and return 'crashed'. restart closes and
        reopens the same file and returns 'restarted'. read uses a separate connection and
        returns a durable snapshot. Return results plus final epochs, leases and outputs;
        snapshots use those same three maps. Expired leases remain visible until explicitly
        replaced or released. At most 50 commands. Do not mutate requests or simulate disk
        persistence solely in process memory.
    """)
    return [
        Task(
            "R22",
            "Atomic resource grants reuse retired tokens and admit partial fenced writes",
            "hard",
            "atomic_scoped_grants_versioned_fencing",
            contract,
            files,
            faults,
            mutants,
            tuple(cases()),
            ("nist-sms",),
            version="2.0",
            difficulty_reason="Coordinate durable independent epoch allocators, atomic set acquisition, partial renewal/release, complete ownership and revision read sets, transactional multi-key output publication and crash recovery across four modules.",
        )
    ]


def cases():
    def acquire(resources=("x",), owner="a", now=0, ttl=10, **kw):
        return dict(
            op="acquire", resources=list(resources), owner=owner, now=now, ttl=ttl, **kw
        )

    def command(op, tokens=None, owner="a", now=1, **kw):
        return dict(op=op, tokens=tokens or {"x": 1}, owner=owner, now=now, **kw)

    def write(tokens=None, expected=None, updates=None, **kw):
        return command(
            "write",
            tokens=tokens,
            expected=expected or {"x": 0},
            updates=updates or {"x": "ok"},
            **kw,
        )

    restart = dict(op="restart")

    def case(
        name, commands, results, epochs=None, leases=None, outputs=None, public=False
    ):
        return Case(
            name,
            dict(resources=["x", "y"], commands=commands),
            dict(
                results=results,
                epochs=epochs or {"x": 0, "y": 0},
                leases=leases or {},
                outputs=outputs or {"x": [0, None], "y": [0, None]},
            ),
            public=public,
        )

    yield case("empty", [], [], public=True)
    yield case(
        "one_grant",
        [acquire()],
        [{"x": 1}],
        epochs={"x": 1, "y": 0},
        leases={"x": ["a", 1, 10]},
        public=True,
    )
    yield case(
        "mixed_busy_grant_rolls_back",
        [acquire(), acquire(["x", "y"], owner="b", now=1)],
        [{"x": 1}, None],
        epochs={"x": 1, "y": 0},
        leases={"x": ["a", 1, 10]},
        public=True,
    )
    yield case(
        "release_reopen_reacquire",
        [acquire(), command("release"), restart, acquire(now=2)],
        [{"x": 1}, True, "restarted", {"x": 2}],
        epochs={"x": 2, "y": 0},
        leases={"x": ["a", 2, 12]},
        public=True,
    )
    yield case(
        "busy_grant_then_reopen_free_resource",
        [
            acquire(),
            acquire(["y", "x"], owner="b", now=1),
            restart,
            acquire(["y"], owner="b", now=2),
        ],
        [{"x": 1}, None, "restarted", {"y": 1}],
        epochs={"x": 1, "y": 1},
        leases={"x": ["a", 1, 10], "y": ["b", 1, 12]},
    )
    yield case(
        "same_owner_stale_token",
        [acquire(), acquire(now=10), write(now=11)],
        [{"x": 1}, {"x": 2}, False],
        epochs={"x": 2, "y": 0},
        leases={"x": ["a", 2, 20]},
    )
    yield case(
        "wrong_owner",
        [acquire(), write(owner="b")],
        [{"x": 1}, False],
        epochs={"x": 1, "y": 0},
        leases={"x": ["a", 1, 10]},
    )
    yield case(
        "expiry_boundary",
        [acquire(), write(now=10)],
        [{"x": 1}, False],
        epochs={"x": 1, "y": 0},
        leases={"x": ["a", 1, 10]},
    )
    yield case(
        "renew_never_shortens",
        [acquire(), command("renew", ttl=1), write(now=5)],
        [{"x": 1}, True, True],
        epochs={"x": 1, "y": 0},
        leases={"x": ["a", 1, 10]},
        outputs={"x": [1, "ok"], "y": [0, None]},
    )
    yield case(
        "crashed_acquisition_reuses_uncommitted_epoch",
        [acquire(crash=True), restart, acquire(now=2)],
        ["crashed", "restarted", {"x": 1}],
        epochs={"x": 1, "y": 0},
        leases={"x": ["a", 1, 12]},
    )
    yield case(
        "successful_multiwrite",
        [
            acquire(["x", "y"]),
            write(
                tokens={"x": 1, "y": 1},
                expected={"x": 0, "y": 0},
                updates={"x": "a", "y": "b"},
            ),
            restart,
        ],
        [{"x": 1, "y": 1}, True, "restarted"],
        epochs={"x": 1, "y": 1},
        leases={"x": ["a", 1, 10], "y": ["a", 1, 10]},
        outputs={"x": [1, "a"], "y": [1, "b"]},
    )
    yield case(
        "missing_token_scope",
        [acquire(), write(updates={"x": "a", "y": "b"}, expected={"x": 0, "y": 0})],
        [{"x": 1}, False],
        epochs={"x": 1, "y": 0},
        leases={"x": ["a", 1, 10]},
    )
    yield case(
        "stale_output_revision",
        [acquire(), write(), write(now=2, updates={"x": "bad"})],
        [{"x": 1}, True, False],
        epochs={"x": 1, "y": 0},
        leases={"x": ["a", 1, 10]},
        outputs={"x": [1, "ok"], "y": [0, None]},
    )
    yield case(
        "crashed_write",
        [acquire(), write(crash=True), restart],
        [{"x": 1}, "crashed", "restarted"],
        epochs={"x": 1, "y": 0},
        leases={"x": ["a", 1, 10]},
    )
    yield case(
        "partial_release_bad_token",
        [acquire(["x", "y"]), command("release", tokens={"x": 1, "y": 2})],
        [{"x": 1, "y": 1}, False],
        epochs={"x": 1, "y": 1},
        leases={"x": ["a", 1, 10], "y": ["a", 1, 10]},
    )
    yield case(
        "independent_epochs",
        [acquire(), command("release"), acquire(["x", "y"], now=2)],
        [{"x": 1}, True, {"x": 2, "y": 1}],
        epochs={"x": 2, "y": 1},
        leases={"x": ["a", 2, 12], "y": ["a", 1, 12]},
    )
    yield case(
        "duplicate_resource_is_set",
        [acquire(["x", "x"])],
        [{"x": 1}],
        epochs={"x": 1, "y": 0},
        leases={"x": ["a", 1, 10]},
    )
    yield case(
        "crashed_renewal",
        [acquire(), command("renew", ttl=20, crash=True), restart],
        [{"x": 1}, "crashed", "restarted"],
        epochs={"x": 1, "y": 0},
        leases={"x": ["a", 1, 10]},
    )
    yield case(
        "crashed_release",
        [acquire(), command("release", crash=True), restart],
        [{"x": 1}, "crashed", "restarted"],
        epochs={"x": 1, "y": 0},
        leases={"x": ["a", 1, 10]},
    )
    yield case(
        "validation_precedes_crash",
        [acquire(), write(tokens={"x": 9}, crash=True)],
        [{"x": 1}, False],
        epochs={"x": 1, "y": 0},
        leases={"x": ["a", 1, 10]},
    )
    state = dict(
        epochs={"x": 1, "y": 0},
        leases={"x": ["a", 1, 10]},
        outputs={"x": [1, "ok"], "y": [0, None]},
    )
    yield case(
        "independent_reader",
        [acquire(), write(), dict(op="read")],
        [{"x": 1}, True, state],
        **state,
    )
