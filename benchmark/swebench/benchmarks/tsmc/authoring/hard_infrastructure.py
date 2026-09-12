"""Coupled recovery and integrity repairs inspired by NIST SMS dissemination.

The service interfaces and failures are synthetic. NIST supplies operational
context, not source code, fixture records, or reports of these failures.
"""

import hashlib
import json

from .schema import Case, Change, Task, code


def tasks():
    yield publication_task()
    yield package_task()
    yield snapshot_task()
    yield ingest_task()


def publication_task():
    files = {
        "fabops/store.py": code('''
            """Persist the publication intent and each channel acknowledgement."""
            import json
            import sqlite3

            CHANNELS = ("vds", "qdr", "tdp")

            def connect(path):
                db = sqlite3.connect(path)
                db.executescript("""
                    CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, body TEXT);
                    CREATE TABLE IF NOT EXISTS acks (id TEXT, channel TEXT, PRIMARY KEY(id,channel));
                    CREATE TABLE IF NOT EXISTS receipts (id TEXT, channel TEXT);
                    CREATE TABLE IF NOT EXISTS projection (channel TEXT, artifact TEXT, revision INTEGER,
                        payload TEXT, PRIMARY KEY(channel,artifact));
                """)
                return db

            def enqueue(db, command):
                event = command["event"]
                body = json.dumps(event, sort_keys=True, separators=(",", ":"))
                old = db.execute("SELECT body FROM events WHERE id=?", (event["id"],)).fetchone()
                if old:
                    return "duplicate" if old[0] == body else "conflict"
                db.execute("BEGIN IMMEDIATE")
                try:
                    db.execute("INSERT INTO events VALUES (?,?)", (event["id"], body))
                    if command.get("crash", False):
                        raise RuntimeError("interrupted enqueue")
                    db.commit()
                    return "queued"
                except RuntimeError:
                    db.rollback()
                    return "crashed"

            def pending(db):
                return [[event, channel] for (event,) in db.execute("SELECT id FROM events ORDER BY id")
                        for channel in CHANNELS if not db.execute(
                            "SELECT 1 FROM acks WHERE id=? AND channel=?", (event, channel)).fetchone()]
        '''),
        "fabops/sink.py": code('''
            """The downstream commit is deliberately separate from the outbox ack."""
            def publish(db, channel, event):
                db.execute("BEGIN IMMEDIATE")
                try:
                    receipt = db.execute("SELECT 1 FROM receipts WHERE id=? AND channel=?",
                                         (event["id"], channel)).fetchone()
                    if receipt is not None:
                        db.commit()
                        return
                    db.execute("INSERT INTO receipts VALUES (?,?)", (event["id"], channel))
                    current = db.execute("SELECT revision FROM projection WHERE channel=? AND artifact=?",
                                         (channel, event["artifact"])).fetchone()
                    if current is None or event["revision"] > current[0]:
                        db.execute("INSERT OR REPLACE INTO projection VALUES (?,?,?,?)",
                                   (channel, event["artifact"], event["revision"], event["payload"]))
                    db.commit()
                except Exception:
                    db.rollback()
                    raise
        '''),
        "fabops/delivery.py": code('''
            """Reconcile a committed delivery without assuming the ack reached disk."""
            import json
            from .sink import publish

            def deliver(db, event_id, channel, crash="none"):
                row = db.execute("SELECT body FROM events WHERE id=?", (event_id,)).fetchone()
                if row is None:
                    return "missing"
                if db.execute("SELECT 1 FROM acks WHERE id=? AND channel=?", (event_id, channel)).fetchone():
                    return "acked"
                if crash == "before_sink":
                    return "crashed"
                publish(db, channel, json.loads(row[0]))
                if crash == "after_sink":
                    return "crashed"
                db.execute("INSERT OR IGNORE INTO acks VALUES (?,?)", (event_id, channel))
                db.commit()
                return "acked"
        '''),
        "fabops/domain.py": code("""
            import tempfile
            from pathlib import Path
            from .store import CHANNELS, connect, enqueue, pending
            from .delivery import deliver

            def run(request):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "publication.sqlite"
                    db = connect(path)
                    results = []
                    try:
                        for command in request["commands"]:
                            op = command["op"]
                            if op == "enqueue":
                                results.append(enqueue(db, command))
                            elif op == "deliver":
                                results.append(deliver(db, command["id"], command["channel"], command.get("crash", "none")))
                            elif op == "reconcile":
                                for event_id, channel in pending(db):
                                    deliver(db, event_id, channel)
                                results.append("reconciled")
                            else:
                                db.close()
                                db = connect(path)
                                results.append("restarted")
                        projections = {channel: {} for channel in CHANNELS}
                        for channel, artifact, revision, payload in db.execute("SELECT * FROM projection"):
                            projections[channel][artifact] = [revision, payload]
                        return dict(results=results, pending=pending(db), projections=projections,
                                    receipts=db.execute("SELECT COUNT(*) FROM receipts").fetchone()[0])
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
        Change(
            "fabops/delivery.py",
            'if crash == "before_sink":',
            'db.execute("INSERT OR IGNORE INTO acks VALUES (?,?)", (event_id, channel))\n    db.commit()\n    if crash == "before_sink":',
        ),
        Change(
            "fabops/sink.py",
            '(event["id"], channel)).fetchone()',
            '(event["artifact"], channel)).fetchone()',
        ),
        Change(
            "fabops/sink.py",
            'if current is None or event["revision"] > current[0]:',
            'if current is None or event["revision"] != current[0]:',
        ),
    )
    return Task(
        "R29",
        "Publication recovery loses a channel or replays obsolete artifact revisions",
        "hard",
        "durable_multichannel_outbox_reconciliation",
        "A local simulation of three independently acknowledged dissemination channels (vds, qdr, tdp) "
        "uses a real SQLite file. enqueue(event,crash=false) atomically records an immutable event with "
        "id, artifact, positive revision and string payload. Return queued, duplicate for identical retry "
        "ignoring JSON object key order, conflict for a changed event under the same id, or crashed with "
        "no durable intent if interrupted before commit. Distinct event ids for one artifact have distinct "
        "revisions. deliver(id,channel,crash=none) returns missing if no event, acked if already acked, "
        "otherwise crashed at before_sink or after_sink. before_sink has no effects; after_sink commits "
        "the downstream receipt and projection but leaves the local ack pending. A normal delivery commits "
        "the sink first and then the ack. Each (id,channel) can have only one downstream receipt even "
        "after restart or lost ack. The per-channel artifact projection retains the greatest delivered "
        "revision; an older delivery still gets its receipt and ack. reconcile retries every pending "
        "delivery in lexicographic event-id order and channel order vds,qdr,tdp, returning reconciled. "
        "restart closes and reopens the same file, returning restarted. Return command results, pending "
        "[id,channel] pairs in that order, projections for all three channels, and total receipt count. "
        "A sink commit and its ack must remain separate real transactions so injected failures exercise "
        "durable recovery; process memory is not durable storage.",
        files,
        faults,
        dict(
            zip(
                (
                    "enqueue_commits_early",
                    "ack_precedes_delivery",
                    "duplicate_sink_effect",
                    "stale_projection",
                ),
                ((f,) for f in faults),
            )
        ),
        tuple(publication_cases()),
        ("nist-sms",),
        difficulty_reason="Coordinate four coupled invariants across SQLite intent atomicity, an independently committed sink, lost acknowledgements, per-channel idempotence and monotonic projections. Unlike a single outbox or lease check, a successful retry must repair channel divergence without duplicating a remote effect or rolling back a newer revision.",
    )


def publication_cases():
    def en(key="e1", revision=1, payload="a", artifact="lot", crash=False):
        return {
            "op": "enqueue",
            "event": {
                "id": key,
                "artifact": artifact,
                "revision": revision,
                "payload": payload,
            },
            "crash": crash,
        }

    def de(key="e1", channel="qdr", crash="none"):
        return {"op": "deliver", "id": key, "channel": channel, "crash": crash}

    restart, reconcile = {"op": "restart"}, {"op": "reconcile"}
    all_pending = [["e1", "vds"], ["e1", "qdr"], ["e1", "tdp"]]
    q_pending = [["e1", "vds"], ["e1", "tdp"]]
    rows = [
        ("empty", [], [], [], [{}, {}, {}], 0),
        (
            "one_complete",
            [en(), reconcile],
            ["queued", "reconciled"],
            [],
            [{"lot": [1, "a"]}] * 3,
            3,
        ),
        (
            "lost_ack_recovery",
            [en(), de(crash="after_sink"), restart, reconcile],
            ["queued", "crashed", "restarted", "reconciled"],
            [],
            [{"lot": [1, "a"]}] * 3,
            3,
        ),
        (
            "interrupted_intent",
            [en(crash=True), restart, reconcile],
            ["crashed", "restarted", "reconciled"],
            [],
            [{}, {}, {}],
            0,
        ),
        (
            "pending_intent",
            [en(), restart],
            ["queued", "restarted"],
            all_pending,
            [{}, {}, {}],
            0,
        ),
        (
            "pre_sink_recovery",
            [en(), de(crash="before_sink"), restart, reconcile],
            ["queued", "crashed", "restarted", "reconciled"],
            [],
            [{"lot": [1, "a"]}] * 3,
            3,
        ),
        (
            "lost_ack_unreconciled",
            [en(), de(crash="after_sink")],
            ["queued", "crashed"],
            all_pending,
            [{}, {"lot": [1, "a"]}, {}],
            1,
        ),
        (
            "one_channel_only",
            [en(), de()],
            ["queued", "acked"],
            q_pending,
            [{}, {"lot": [1, "a"]}, {}],
            1,
        ),
        (
            "acked_retry",
            [en(), de(), de()],
            ["queued", "acked", "acked"],
            q_pending,
            [{}, {"lot": [1, "a"]}, {}],
            1,
        ),
        (
            "two_lost_acks",
            [en(), de(crash="after_sink"), de(crash="after_sink"), de()],
            ["queued", "crashed", "crashed", "acked"],
            q_pending,
            [{}, {"lot": [1, "a"]}, {}],
            1,
        ),
        (
            "older_reconciled_last",
            [en("z", 1, "old"), en("a", 2, "new"), reconcile],
            ["queued", "queued", "reconciled"],
            [],
            [{"lot": [2, "new"]}] * 3,
            6,
        ),
        (
            "stale_lost_ack",
            [
                en(),
                en("e2", 2, "new"),
                de("e2"),
                de(crash="after_sink"),
                restart,
                reconcile,
            ],
            ["queued", "queued", "acked", "crashed", "restarted", "reconciled"],
            [],
            [{"lot": [2, "new"]}] * 3,
            6,
        ),
        (
            "conflicting_id",
            [en(), en(payload="bad"), reconcile],
            ["queued", "conflict", "reconciled"],
            [],
            [{"lot": [1, "a"]}] * 3,
            3,
        ),
        (
            "duplicate_enqueue",
            [en(), en(), reconcile, reconcile],
            ["queued", "duplicate", "reconciled", "reconciled"],
            [],
            [{"lot": [1, "a"]}] * 3,
            3,
        ),
        ("missing_delivery", [de("absent")], ["missing"], [], [{}, {}, {}], 0),
        (
            "failed_intent_retry",
            [en(crash=True), en(), reconcile],
            ["crashed", "queued", "reconciled"],
            [],
            [{"lot": [1, "a"]}] * 3,
            3,
        ),
        (
            "independent_artifacts",
            [en(), en("e2", 1, "b", "tool"), reconcile],
            ["queued", "queued", "reconciled"],
            [],
            [{"lot": [1, "a"], "tool": [1, "b"]}] * 3,
            6,
        ),
    ]
    for index, (name, commands, results, pending, projections, receipts) in enumerate(
        rows
    ):
        yield Case(
            name,
            {"commands": commands},
            {
                "results": results,
                "pending": pending,
                "projections": dict(zip(("vds", "qdr", "tdp"), projections)),
                "receipts": receipts,
            },
            public=index < 4,
        )


def package_task():
    files = {
        "fabops/graph.py": code('''
            """Resolve the exact pinned revision closure before publishing a package."""
            def closure(artifacts, roots):
                catalog = {(row["id"], row["revision"]): row for row in artifacts}
                selected, active, done, ordered = {}, set(), set(), []

                def visit(key):
                    key = tuple(key)
                    if key in active:
                        raise ValueError("dependency cycle")
                    if key[0] in selected and selected[key[0]] != key[1]:
                        raise ValueError("incompatible revision pins")
                    selected[key[0]] = key[1]
                    if key in done:
                        return
                    row = catalog.get(key)
                    if row is None or row["revoked"]:
                        raise ValueError("missing or revoked artifact")
                    active.add(key)
                    done.add(key)
                    for dependency in sorted(row["requires"]):
                        visit(dependency)
                    active.remove(key)
                    ordered.append(row)

                for root in sorted(roots):
                    visit(root)
                return ordered
        '''),
        "fabops/package.py": code('''
            """Verify every linked object and atomically replace the installed manifest."""
            import hashlib
            import sqlite3
            from .graph import closure

            def connect(path):
                db = sqlite3.connect(path)
                db.execute("CREATE TABLE IF NOT EXISTS installed (position INTEGER PRIMARY KEY, id TEXT, revision INTEGER, content TEXT)")
                db.commit()
                return db

            def install(db, artifacts, roots, crash=False):
                try:
                    ordered = closure(artifacts, roots)
                    for row in ordered:
                        if hashlib.sha256(row["content"].encode("utf-8")).hexdigest() != row["sha256"]:
                            raise ValueError("content digest mismatch")
                except ValueError:
                    return "invalid"
                db.execute("BEGIN IMMEDIATE")
                try:
                    db.execute("DELETE FROM installed")
                    if crash:
                        raise RuntimeError("interrupted package replacement")
                    db.executemany("INSERT INTO installed VALUES (?,?,?,?)", [
                        (index, row["id"], row["revision"], row["content"])
                        for index, row in enumerate(ordered)])
                    db.commit()
                    return "installed"
                except RuntimeError:
                    db.rollback()
                    return "crashed"
        '''),
        "fabops/domain.py": code("""
            import tempfile
            from pathlib import Path
            from .package import connect, install

            def run(request):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "package.sqlite"
                    db = connect(path)
                    results = []
                    try:
                        for command in request["commands"]:
                            if command["op"] == "restart":
                                db.close()
                                db = connect(path)
                                results.append("restarted")
                            else:
                                results.append(install(db, request["artifacts"], command["roots"], command.get("crash", False)))
                        installed = [list(row) for row in db.execute("SELECT id,revision,content FROM installed ORDER BY position")]
                        return dict(results=results, installed=installed)
                    finally:
                        db.close()
        """),
    }
    faults = (
        Change(
            "fabops/graph.py",
            "row = catalog.get(key)",
            'row = max((row for (name, revision), row in catalog.items() if name == key[0]), key=lambda row: row["revision"], default=None)',
        ),
        Change(
            "fabops/graph.py",
            "if key in active:",
            "if key in active and key not in done:",
        ),
        Change(
            "fabops/graph.py",
            "if key[0] in selected and selected[key[0]] != key[1]:",
            "if key[0] in selected and selected[key[0]] > key[1]:",
        ),
        Change(
            "fabops/package.py",
            "for row in ordered:\n            if hashlib",
            'for row in ordered:\n            if [row["id"], row["revision"]] not in roots:\n                continue\n            if hashlib',
        ),
        Change(
            "fabops/package.py",
            'db.execute("DELETE FROM installed")',
            'db.execute("DELETE FROM installed")\n        db.commit()',
        ),
    )
    return Task(
        "R30",
        "Technical package assembly mixes revisions and destroys the last valid package",
        "hard",
        "pinned_revision_closure_atomic_package_install",
        "artifacts is an unordered catalog with unique (id,revision) pairs. Each entry has a string id, "
        "positive integer revision, UTF-8 content, declared lowercase sha256, revoked boolean, and requires "
        "containing exact [id,revision] references. install(roots,crash=false) resolves the complete reachable "
        "closure of exact roots, never the latest revision. Missing or revoked reachable entries, dependency "
        "cycles, two revisions of one id in the closure, or a content/digest mismatch anywhere in the closure "
        "return invalid and preserve the current package. Unreachable bad entries are ignored. Traverse "
        "roots sorted by (id,revision), recursively visit dependencies in that same order, emit each node "
        "once after its dependencies; duplicate roots/dependencies and diamond sharing are allowed. On "
        "success atomically replace all installed rows in a real SQLite transaction and return installed. "
        "An injected crash after deleting the previous rows but before inserting replacements returns "
        "crashed and must preserve the previous package across restart. Empty roots install an empty "
        "package. restart closes/reopens the same file and returns restarted. Return results and installed "
        "[id,revision,content] rows in dependency traversal order. Validation precedes the crash point. "
        "The graph may contain up to 40 revisions and arbitrary sharing, cycles and conflicting pins.",
        files,
        faults,
        dict(
            zip(
                (
                    "latest_revision_substitution",
                    "cycle_masked_as_shared_node",
                    "conflicting_pins_accepted",
                    "root_only_integrity",
                    "destructive_precommit",
                ),
                ((f,) for f in faults),
            )
        ),
        tuple(package_cases()),
        ("nist-sms",),
        difficulty_reason="Resolve a revision-pinned graph with shared dependencies, cycles and incompatible pins; verify all reachable content; then preserve the last complete installed package across a real interrupted replacement. The coupled graph/integrity/publication boundary differs from a one-table schema migration.",
    )


def package_cases():
    def artifact(name, revision=1, content=None, requires=(), bad=False, revoked=False):
        content = name if content is None else content
        return {
            "id": name,
            "revision": revision,
            "content": content,
            "requires": list(requires),
            "revoked": revoked,
            "sha256": "0" * 64 if bad else hashlib.sha256(content.encode()).hexdigest(),
        }

    def install(*roots, crash=False):
        return {"op": "install", "roots": list(roots), "crash": crash}

    restart = {"op": "restart"}
    a = artifact("a")
    chain = [
        artifact("a", requires=[["b", 1]]),
        artifact("b", requires=[["c", 1]]),
        artifact("c"),
    ]
    rows = [
        ("empty", [], [], [], []),
        ("one", [a], [install(["a", 1])], ["installed"], [["a", 1, "a"]]),
        (
            "pinned_old_revision",
            [a, artifact("a", 2, "new")],
            [install(["a", 1])],
            ["installed"],
            [["a", 1, "a"]],
        ),
        (
            "failed_replacement",
            [a, artifact("b")],
            [install(["a", 1]), install(["b", 1], crash=True), restart],
            ["installed", "crashed", "restarted"],
            [["a", 1, "a"]],
        ),
        (
            "transitive_closure",
            chain,
            [install(["a", 1])],
            ["installed"],
            [["c", 1, "c"], ["b", 1, "b"], ["a", 1, "a"]],
        ),
        (
            "diamond",
            [
                artifact("a", requires=[["c", 1], ["b", 1]]),
                artifact("b", requires=[["d", 1]]),
                artifact("c", requires=[["d", 1]]),
                artifact("d"),
            ],
            [install(["a", 1])],
            ["installed"],
            [["d", 1, "d"], ["b", 1, "b"], ["c", 1, "c"], ["a", 1, "a"]],
        ),
        (
            "self_cycle",
            [artifact("a", requires=[["a", 1]])],
            [install(["a", 1])],
            ["invalid"],
            [],
        ),
        (
            "indirect_cycle",
            [
                artifact("a", requires=[["b", 1]]),
                artifact("b", requires=[["c", 1]]),
                artifact("c", requires=[["a", 1]]),
            ],
            [install(["a", 1])],
            ["invalid"],
            [],
        ),
        (
            "incompatible_roots",
            [a, artifact("a", 2, "new")],
            [install(["a", 1], ["a", 2])],
            ["invalid"],
            [],
        ),
        (
            "transitive_pin_conflict",
            [
                artifact("a", requires=[["c", 1]]),
                artifact("b", requires=[["c", 2]]),
                artifact("c"),
                artifact("c", 2, "new"),
            ],
            [install(["a", 1], ["b", 1])],
            ["invalid"],
            [],
        ),
        (
            "bad_leaf_digest",
            [artifact("a", requires=[["b", 1]]), artifact("b", bad=True)],
            [install(["a", 1])],
            ["invalid"],
            [],
        ),
        (
            "missing_exact_revision",
            [artifact("a", requires=[["b", 2]]), artifact("b")],
            [install(["a", 1])],
            ["invalid"],
            [],
        ),
        (
            "revoked_dependency",
            [artifact("a", requires=[["b", 1]]), artifact("b", revoked=True)],
            [install(["a", 1])],
            ["invalid"],
            [],
        ),
        (
            "unreachable_corruption",
            [a, artifact("bad", bad=True, requires=[["missing", 9]])],
            [install(["a", 1]), restart],
            ["installed", "restarted"],
            [["a", 1, "a"]],
        ),
        (
            "duplicate_shared_roots",
            [artifact("a", requires=[["b", 1], ["b", 1]]), artifact("b")],
            [install(["b", 1], ["a", 1], ["a", 1])],
            ["installed"],
            [["b", 1, "b"], ["a", 1, "a"]],
        ),
        (
            "invalid_preserves_existing",
            [a, artifact("b", bad=True)],
            [install(["a", 1]), install(["b", 1], crash=True), restart],
            ["installed", "invalid", "restarted"],
            [["a", 1, "a"]],
        ),
        (
            "retry_interrupted_replacement",
            [a, artifact("b")],
            [
                install(["a", 1]),
                install(["b", 1], crash=True),
                restart,
                install(["b", 1]),
            ],
            ["installed", "crashed", "restarted", "installed"],
            [["b", 1, "b"]],
        ),
        (
            "empty_replacement",
            [a],
            [install(["a", 1]), install()],
            ["installed", "installed"],
            [],
        ),
        (
            "failed_empty_replacement",
            [a],
            [install(["a", 1]), install(crash=True), restart],
            ["installed", "crashed", "restarted"],
            [["a", 1, "a"]],
        ),
        (
            "unicode_content",
            [artifact("a", content="\u03bcm\n")],
            [install(["a", 1])],
            ["installed"],
            [["a", 1, "\u03bcm\n"]],
        ),
    ]
    for index, (name, artifacts, commands, results, installed) in enumerate(rows):
        yield Case(
            name,
            {"artifacts": artifacts, "commands": commands},
            {"results": results, "installed": installed},
            public=index < 4,
        )


def snapshot_task():
    files = {
        "fabops/stream.py": code('''
            """Track a source's contiguous prefix independently of delivery order."""
            import copy

            def initial(epoch=0):
                return dict(epoch=epoch, next=1, watermark=-1, events={}, barriers=[])

            def accept(previous, page):
                if page["epoch"] < previous["epoch"]:
                    return "stale", previous
                state = copy.deepcopy(previous)
                if page["epoch"] > state["epoch"]:
                    state = initial(page["epoch"])
                for event in page["events"]:
                    key = str(event["sequence"])
                    old = state["events"].get(key)
                    if old is not None and old != event:
                        return "conflict", previous
                    state["events"][key] = dict(event)
                state["barriers"].append([page["through"], page["watermark"]])
                while str(state["next"]) in state["events"]:
                    state["next"] += 1
                ready = [watermark for through, watermark in state["barriers"] if through < state["next"]]
                state["watermark"] = max([state["watermark"]] + ready)
                state["barriers"] = [[through, watermark] for through, watermark in state["barriers"] if through >= state["next"]]
                return "accepted", state
        '''),
        "fabops/snapshot.py": code('''
            """Materialize a time cut that every source can certify as complete."""
            def materialize(states):
                watermarks = [state["watermark"] for state in states.values()]
                if any(value < 0 for value in watermarks):
                    return None
                cut = min(watermarks)
                values = {}
                for source, state in states.items():
                    eligible = [event for event in state["events"].values()
                                if event["sequence"] < state["next"] and event["time"] <= cut]
                    latest = max(eligible, key=lambda event: event["sequence"], default=None)
                    values[source] = latest["value"] if latest is not None else None
                return dict(cut=cut, epochs={source: state["epoch"] for source, state in states.items()}, values=values)
        '''),
        "fabops/checkpoint.py": code('''
            """Persist unresolved buffers and the last published cut in one checkpoint."""
            import copy
            import json
            import sqlite3

            def connect(path):
                db = sqlite3.connect(path)
                db.execute("CREATE TABLE IF NOT EXISTS checkpoint (id INTEGER PRIMARY KEY, payload TEXT)")
                db.commit()
                return db

            def save(db, states, published, crash=False):
                durable = copy.deepcopy(states)
                payload = json.dumps(dict(states=durable, published=published), sort_keys=True)
                db.execute("BEGIN IMMEDIATE")
                try:
                    db.execute("INSERT OR REPLACE INTO checkpoint VALUES (1,?)", (payload,))
                    if crash:
                        raise RuntimeError("interrupted checkpoint")
                    db.commit()
                except RuntimeError:
                    db.rollback()
                    raise

            def load(db):
                row = db.execute("SELECT payload FROM checkpoint WHERE id=1").fetchone()
                data = json.loads(row[0])
                return data["states"], data["published"]
        '''),
        "fabops/domain.py": code("""
            import tempfile
            from pathlib import Path
            from .stream import initial, accept
            from .snapshot import materialize
            from .checkpoint import connect, load, save

            def run(request):
                states = {source: initial() for source in request["sources"]}
                published, results = None, []
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "snapshots.sqlite"
                    db = connect(path)
                    try:
                        save(db, states, published)
                        for command in request["commands"]:
                            if command["op"] == "restart":
                                db.close()
                                db = connect(path)
                                states, published = load(db)
                                results.append("restarted")
                                continue
                            candidate, next_published = dict(states), published
                            if command["op"] == "page":
                                source = command["source"]
                                result, candidate[source] = accept(states[source], command)
                            else:
                                snapshot = materialize(states)
                                result = "blocked" if snapshot is None else "published"
                                if snapshot is not None:
                                    next_published = snapshot
                            if result in {"accepted", "published"}:
                                try:
                                    save(db, candidate, next_published, command.get("crash", False))
                                    states, published = candidate, next_published
                                except RuntimeError:
                                    result = "crashed"
                            results.append(result)
                        frontiers = {source: [state["epoch"], state["next"], state["watermark"]] for source, state in states.items()}
                        return dict(results=results, snapshot=published, frontiers=frontiers)
                    finally:
                        db.close()
        """),
    }
    faults = (
        Change(
            "fabops/stream.py",
            'state = initial(page["epoch"])',
            'state = dict(initial(page["epoch"]), watermark=previous["watermark"])',
        ),
        Change(
            "fabops/stream.py",
            'while str(state["next"]) in state["events"]:\n        state["next"] += 1',
            'state["next"] = max([state["next"] - 1] + [int(key) for key in state["events"]]) + 1',
        ),
        Change("fabops/snapshot.py", "cut = min(watermarks)", "cut = max(watermarks)"),
        Change(
            "fabops/checkpoint.py",
            "durable = copy.deepcopy(states)",
            'durable = copy.deepcopy(states)\n    for state in durable.values():\n        state["events"] = {key: value for key, value in state["events"].items() if int(key) < state["next"]}',
        ),
        Change(
            "fabops/checkpoint.py",
            "if crash:\n            raise",
            "db.commit()\n        if crash:\n            raise",
        ),
    )
    return Task(
        "R31",
        "Recovered telemetry snapshots combine incomplete prefixes and obsolete source epochs",
        "hard",
        "multisource_epoch_barrier_snapshot_recovery",
        "sources lists 1-4 unique source ids. Each starts in epoch 0 with next sequence 1 and watermark -1. "
        "page(source,epoch,events,through,watermark,crash=false) accepts an unordered batch of unique positive "
        "sequence numbers with nonnegative integer time and integer value. Retain out-of-order events "
        "across real SQLite checkpoint/restart, advance next only through the contiguous prefix starting "
        "at 1, and defer each (through,watermark) barrier until every sequence <=through is present. "
        "The effective watermark is the maximum activated barrier (initially -1). Event time is "
        "nondecreasing with sequence within an epoch; valid barriers guarantee all later-sequence events "
        "have time greater than that barrier's watermark. Advertisements may arrive before their events. "
        "An identical event retry is accepted. A conflicting duplicate sequence rejects the entire page "
        "with conflict and no effects. A lower epoch returns stale; a higher epoch resets the entire "
        "source, including watermark, buffered events and barriers, before accepting the page. Other "
        "sources are unaffected. snapshot(crash=false) is blocked if any source watermark is -1; otherwise "
        "publish cut=min(all source watermarks), the epoch vector, and each source's last contiguous "
        "event value at time<=cut (highest sequence breaks tied times; None if none). A blocked snapshot "
        "preserves the previously published snapshot. Accepted pages and published snapshots checkpoint "
        "states and published value atomically. crash interrupts that checkpoint after its SQL write "
        "but before commit, returns crashed and changes neither memory nor reopened disk state. restart "
        "closes/reopens the actual file and returns restarted. Return results, the last published snapshot "
        "(initially None), and frontiers mapping sources to [epoch,next,watermark]. Snapshot history remains "
        "valid until replaced, even if a source enters a new epoch.",
        files,
        faults,
        dict(
            zip(
                (
                    "retains_old_epoch_watermark",
                    "jumps_over_sequence_gap",
                    "fastest_source_cut",
                    "drops_pending_on_checkpoint",
                    "checkpoint_commits_early",
                ),
                ((f,) for f in faults),
            )
        ),
        tuple(snapshot_cases()),
        ("nist-sms",),
        difficulty_reason="Reconcile out-of-order event buffers, epoch resets, delayed watermark barriers and a common multi-source time cut across real checkpoint interruptions. Unlike cursor advancement or consumer retention, publication depends on the interaction of three independent orders: source epoch, sequence continuity and event time, with durable unresolved state.",
    )


def snapshot_cases():
    def page(source="a", events=(), through=0, watermark=-1, epoch=0, crash=False):
        return {
            "op": "page",
            "source": source,
            "epoch": epoch,
            "through": through,
            "watermark": watermark,
            "events": [{"sequence": s, "time": t, "value": v} for s, t, v in events],
            "crash": crash,
        }

    def snap(cut, values, epochs=None):
        return {
            "cut": cut,
            "epochs": epochs or {source: 0 for source in values},
            "values": values,
        }

    publish, restart = {"op": "snapshot"}, {"op": "restart"}
    p1 = page(events=[(1, 2, 10)], through=1, watermark=2)
    p2 = page(events=[(2, 4, 20)], through=2, watermark=4)
    rows = [
        ("empty", ["a"], [], [], None, {"a": [0, 1, -1]}),
        (
            "one_source",
            ["a"],
            [p1, publish],
            ["accepted", "published"],
            snap(2, {"a": 10}),
            {"a": [0, 2, 2]},
        ),
        (
            "gap_survives_restart",
            ["a"],
            [p2, publish, restart, p1, publish],
            ["accepted", "blocked", "restarted", "accepted", "published"],
            snap(4, {"a": 20}),
            {"a": [0, 3, 4]},
        ),
        (
            "slow_source_cut",
            ["a", "b"],
            [
                page(events=[(1, 5, 50)], through=1, watermark=5),
                page("b", [(1, 2, 20)], 1, 2),
                publish,
            ],
            ["accepted", "accepted", "published"],
            snap(2, {"a": None, "b": 20}),
            {"a": [0, 2, 5], "b": [0, 2, 2]},
        ),
        (
            "old_epoch_is_stale",
            ["a"],
            [page(events=[(1, 3, 3)], through=1, watermark=3, epoch=1), p2, publish],
            ["accepted", "stale", "published"],
            snap(3, {"a": 3}, {"a": 1}),
            {"a": [1, 2, 3]},
        ),
        (
            "new_epoch_blocks_snapshot",
            ["a"],
            [
                page(events=[(1, 8, 8)], through=1, watermark=8),
                publish,
                page(events=[(2, 2, 20)], through=2, watermark=2, epoch=1),
                restart,
                publish,
            ],
            ["accepted", "published", "accepted", "restarted", "blocked"],
            snap(8, {"a": 8}),
            {"a": [1, 1, -1]},
        ),
        (
            "reordered_page_drains",
            ["a"],
            [p2, p1, publish],
            ["accepted", "accepted", "published"],
            snap(4, {"a": 20}),
            {"a": [0, 3, 4]},
        ),
        (
            "identical_retry",
            ["a"],
            [p1, p1, restart, publish],
            ["accepted", "accepted", "restarted", "published"],
            snap(2, {"a": 10}),
            {"a": [0, 2, 2]},
        ),
        (
            "conflict_rolls_back_whole_page",
            ["a"],
            [
                p1,
                page(events=[(2, 4, 20), (1, 2, 99)], through=2, watermark=4),
                restart,
                publish,
            ],
            ["accepted", "conflict", "restarted", "published"],
            snap(2, {"a": 10}),
            {"a": [0, 2, 2]},
        ),
        (
            "empty_certified_source",
            ["a"],
            [page(watermark=4), publish],
            ["accepted", "published"],
            snap(4, {"a": None}),
            {"a": [0, 1, 4]},
        ),
        (
            "barrier_ahead_of_data",
            ["a"],
            [page(through=3, watermark=9), p1, p2, publish],
            ["accepted", "accepted", "accepted", "published"],
            snap(4, {"a": 20}),
            {"a": [0, 3, 4]},
        ),
        (
            "snapshot_crash_is_not_publication",
            ["a"],
            [p1, {"op": "snapshot", "crash": True}, restart],
            ["accepted", "crashed", "restarted"],
            None,
            {"a": [0, 2, 2]},
        ),
        (
            "failed_snapshot_keeps_prior_cut",
            ["a"],
            [p1, publish, p2, {"op": "snapshot", "crash": True}, restart],
            ["accepted", "published", "accepted", "crashed", "restarted"],
            snap(2, {"a": 10}),
            {"a": [0, 3, 4]},
        ),
        (
            "page_crash_rolls_back_cursor",
            ["a"],
            [
                p1,
                page(events=[(2, 4, 20)], through=2, watermark=4, crash=True),
                restart,
                publish,
            ],
            ["accepted", "crashed", "restarted", "published"],
            snap(2, {"a": 10}),
            {"a": [0, 2, 2]},
        ),
        (
            "source_epochs_are_independent",
            ["a", "b"],
            [
                page(events=[(1, 1, 7)], through=1, watermark=3, epoch=2),
                page("b", [(1, 2, 8)], 1, 2, epoch=1),
                publish,
            ],
            ["accepted", "accepted", "published"],
            snap(2, {"a": 7, "b": 8}, {"a": 2, "b": 1}),
            {"a": [2, 2, 3], "b": [1, 2, 2]},
        ),
        (
            "exclude_future_value",
            ["a", "b"],
            [
                page(events=[(1, 1, 1), (2, 5, 5)], through=2, watermark=5),
                page("b", [(1, 3, 3)], 1, 3),
                publish,
            ],
            ["accepted", "accepted", "published"],
            snap(3, {"a": 1, "b": 3}),
            {"a": [0, 3, 5], "b": [0, 2, 3]},
        ),
        (
            "unseen_source_blocks",
            ["a", "b"],
            [p1, publish],
            ["accepted", "blocked"],
            None,
            {"a": [0, 2, 2], "b": [0, 1, -1]},
        ),
        (
            "timestamp_tie_uses_sequence",
            ["a"],
            [page(events=[(2, 2, 0), (1, 2, 9)], through=2, watermark=2), publish],
            ["accepted", "published"],
            snap(2, {"a": 0}),
            {"a": [0, 3, 2]},
        ),
        (
            "pending_barrier_and_buffer_survive_two_restarts",
            ["a"],
            [
                page(events=[(3, 6, 30)], through=3, watermark=6),
                restart,
                p1,
                restart,
                p2,
                publish,
            ],
            ["accepted", "restarted", "accepted", "restarted", "accepted", "published"],
            snap(6, {"a": 30}),
            {"a": [0, 4, 6]},
        ),
    ]
    for index, (name, sources, commands, results, snapshot, frontiers) in enumerate(
        rows
    ):
        yield Case(
            name,
            {"sources": sources, "commands": commands},
            {"results": results, "snapshot": snapshot, "frontiers": frontiers},
            public=index < 4,
        )


def ingest_task():
    files = {
        "fabops/manifest.py": code('''
            """Bind a resumable upload to its complete ordered chunk manifest."""
            import hashlib
            import json

            def canonical(value):
                return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

            def normalize(manifest):
                ordered = sorted(manifest, key=lambda item: item["index"])
                if [item["index"] for item in ordered] != list(range(len(ordered))):
                    raise ValueError("chunk indexes must be contiguous from zero")
                return canonical(ordered)

            def verify(rows, expected):
                body = canonical(rows)
                digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
                if len(rows) != expected["rows"] or digest != expected["sha256"]:
                    raise ValueError("chunk does not match manifest")
                return body
        '''),
        "fabops/upload.py": code('''
            """Stage validated chunks durably without exposing an unfinished batch."""
            import json
            import sqlite3
            from .manifest import normalize, verify

            def connect(path):
                db = sqlite3.connect(path, isolation_level=None)
                db.executescript("""
                    CREATE TABLE IF NOT EXISTS uploads (id TEXT PRIMARY KEY, manifest TEXT, status TEXT);
                    CREATE TABLE IF NOT EXISTS chunks (id TEXT, position INTEGER, body TEXT, PRIMARY KEY(id,position));
                    CREATE TABLE IF NOT EXISTS published (id TEXT, position INTEGER, body TEXT, PRIMARY KEY(id,position));
                """)
                return db

            def begin(db, command):
                try:
                    manifest = normalize(command["manifest"])
                except ValueError:
                    return "invalid"
                old = db.execute("SELECT manifest,status FROM uploads WHERE id=?", (command["id"],)).fetchone()
                if old:
                    if old[0] != manifest:
                        return "conflict"
                    return "committed" if old[1] == "committed" else "resumed"
                db.execute("INSERT INTO uploads VALUES (?,?,?)", (command["id"], manifest, "open"))
                return "started"

            def stage(db, command):
                batch, index = command["id"], command["index"]
                upload = db.execute("SELECT manifest,status FROM uploads WHERE id=?", (batch,)).fetchone()
                if upload is None:
                    return "missing"
                if upload[1] == "committed":
                    return "closed"
                manifest = json.loads(upload[0])
                if index < 0 or index >= len(manifest):
                    return "invalid"
                try:
                    body = verify(command["rows"], manifest[index])
                except ValueError:
                    return "invalid"
                old = db.execute("SELECT body FROM chunks WHERE id=? AND position=?", (batch, index)).fetchone()
                if old:
                    return "duplicate" if old[0] == body else "conflict"
                db.execute("INSERT INTO chunks VALUES (?,?,?)", (batch, index, body))
                return "staged"
        '''),
        "fabops/publish.py": code('''
            """Validate cross-chunk constraints and publish all rows in one transaction."""
            import json
            from .manifest import canonical, verify

            def finish(db, batch, crash=False):
                db.execute("BEGIN IMMEDIATE")
                try:
                    upload = db.execute("SELECT manifest,status FROM uploads WHERE id=?", (batch,)).fetchone()
                    if upload is None:
                        db.rollback()
                        return "missing"
                    if upload[1] == "committed":
                        db.commit()
                        return "committed"
                    manifest = json.loads(upload[0])
                    chunks = dict(db.execute("SELECT position,body FROM chunks WHERE id=?", (batch,)))
                    if set(chunks) != set(range(len(manifest))):
                        db.rollback()
                        return "incomplete"
                    rows, seen = [], set()
                    for expected in manifest:
                        chunk = json.loads(chunks[expected["index"]])
                        verify(chunk, expected)
                        for row in chunk:
                            if row["key"] in seen:
                                raise ValueError("duplicate record identity across batch")
                            seen.add(row["key"])
                            rows.append(row)
                    db.executemany("INSERT OR REPLACE INTO published VALUES (?,?,?)",
                                   [(batch, index, canonical(row)) for index, row in enumerate(rows)])
                    if crash:
                        raise RuntimeError("interrupted batch publication")
                    db.execute("UPDATE uploads SET status='committed' WHERE id=?", (batch,))
                    db.commit()
                    return "committed"
                except ValueError:
                    db.rollback()
                    return "invalid"
                except RuntimeError:
                    db.rollback()
                    return "crashed"
        '''),
        "fabops/domain.py": code("""
            import json
            import tempfile
            from pathlib import Path
            from .upload import connect, begin, stage
            from .publish import finish

            def run(request):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "bulk.sqlite"
                    db, results = connect(path), []
                    try:
                        for command in request["commands"]:
                            op = command["op"]
                            if op == "begin":
                                result = begin(db, command)
                            elif op == "chunk":
                                result = stage(db, command)
                            elif op == "finish":
                                result = finish(db, command["id"], command.get("crash", False))
                            else:
                                db.close()
                                db = connect(path)
                                result = "restarted"
                            results.append(result)
                        published = {}
                        for batch, position, body in db.execute("SELECT * FROM published ORDER BY id,position"):
                            published.setdefault(batch, []).append(json.loads(body))
                        for (batch,) in db.execute("SELECT id FROM uploads WHERE status='committed'"):
                            published.setdefault(batch, [])
                        staged = [[batch, position] for batch, position in db.execute("SELECT id,position FROM chunks ORDER BY id,position")]
                        states = dict(db.execute("SELECT id,status FROM uploads ORDER BY id"))
                        return dict(results=results, published=published, staged=staged, states=states)
                    finally:
                        db.close()
        """),
    }
    faults = (
        Change(
            "fabops/manifest.py",
            "return canonical(ordered)",
            "return canonical(manifest)",
        ),
        Change(
            "fabops/manifest.py",
            'if len(rows) != expected["rows"] or digest != expected["sha256"]:',
            'if len(rows) != expected["rows"] and digest != expected["sha256"]:',
        ),
        Change(
            "fabops/publish.py",
            'chunk = json.loads(chunks[expected["index"]])',
            'seen = set()\n            chunk = json.loads(chunks[expected["index"]])',
        ),
        Change(
            "fabops/publish.py",
            "if crash:\n            raise",
            "db.commit()\n        if crash:\n            raise",
        ),
    )
    return Task(
        "R32",
        "Resumed bulk imports expose unverified or partially published manufacturing records",
        "hard",
        "manifest_bound_resumable_atomic_bulk_ingest",
        "A real SQLite file holds isolated named uploads. begin(id,manifest) binds that id to an immutable "
        "manifest of {index,rows,sha256} chunk descriptors; indexes must be exactly 0..n-1 with no duplicates "
        "but input ordering is arbitrary. rows is a nonnegative count. sha256 is the lowercase SHA-256 of "
        "canonical UTF-8 chunk JSON: sorted object keys, compact separators, ensure_ascii=false; list order "
        "matters. begin returns started, resumed for an identical normalized manifest while open, committed "
        "for an identical completed manifest, conflict for a changed manifest, or invalid for invalid indexes. "
        "chunk(id,index,rows) stages a list of {key:string,value:integer} rows only if index, count and digest "
        "match its bound descriptor. Return missing for unknown upload, closed for completed upload, invalid "
        "for verification failure, duplicate for an identical staged retry, conflict for different staged "
        "content, otherwise staged. No staged row is query-visible before finish. finish(id,crash=false) "
        "returns missing, committed if already complete, incomplete if any chunk is absent, or invalid if "
        "any record key repeats across the whole batch. Reverify all chunks inside the publication transaction, "
        "then publish in chunk-index/row order and mark the upload committed atomically. An injected crash "
        "after writing published rows but before status update returns crashed, rolls back all publication "
        "effects and preserves staged chunks for retry. restart reopens the same database and returns "
        "restarted. Empty manifests commit empty batches. Different uploads may reuse record keys. Return "
        "results, published mapping only visible batch ids to row lists, all staged [id,index] pairs sorted "
        "by id/index, and states mapping every begun id to open or committed. Staged chunks are retained "
        "after commit for audit. Implement actual transactional persistence, not in-memory restart simulation.",
        files,
        faults,
        dict(
            zip(
                (
                    "manifest_input_order_identity",
                    "count_or_digest_is_enough",
                    "uniqueness_only_within_chunk",
                    "publication_before_commit_marker",
                ),
                ((f,) for f in faults),
            )
        ),
        tuple(ingest_cases()),
        ("nist-sms",),
        difficulty_reason="Bind resumable staging to a canonical multi-chunk manifest, enforce independent per-chunk and cross-chunk constraints, and separate staged durability from atomic query visibility across restart. This combines hash integrity, scope/order identity and publication recovery rather than a single request fingerprint or schema rollback.",
    )


def ingest_cases():
    def manifest(*chunks):
        # This encodes request digests only; expected states and records are literal.
        return [
            {
                "index": index,
                "rows": len(rows),
                "sha256": hashlib.sha256(
                    json.dumps(
                        rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                    ).encode()
                ).hexdigest(),
            }
            for index, rows in enumerate(chunks)
        ]

    def begin(parts, batch="b"):
        return {"op": "begin", "id": batch, "manifest": parts}

    def chunk(index, rows, batch="b"):
        return {"op": "chunk", "id": batch, "index": index, "rows": rows}

    def finish(batch="b", crash=False):
        return {"op": "finish", "id": batch, "crash": crash}

    restart = {"op": "restart"}
    a, b, bad = (
        [{"key": "a", "value": 1}],
        [{"key": "b", "value": 2}],
        [{"key": "a", "value": 9}],
    )
    one, two = manifest(a), manifest(a, b)
    rows = [
        ("empty", [], [], {}, [], {}),
        (
            "complete_one",
            [begin(one), chunk(0, a), finish()],
            ["started", "staged", "committed"],
            {"b": [{"key": "a", "value": 1}]},
            [["b", 0]],
            {"b": "committed"},
        ),
        (
            "digest_failure_is_not_staged",
            [begin(one), chunk(0, bad), finish()],
            ["started", "invalid", "incomplete"],
            {},
            [],
            {"b": "open"},
        ),
        (
            "crash_before_publication_commit",
            [begin(one), chunk(0, a), finish(crash=True), restart],
            ["started", "staged", "crashed", "restarted"],
            {},
            [["b", 0]],
            {"b": "open"},
        ),
        (
            "reordered_manifest_resume",
            [
                begin(two),
                begin(list(reversed(two))),
                chunk(1, b),
                restart,
                chunk(0, a),
                finish(),
            ],
            ["started", "resumed", "staged", "restarted", "staged", "committed"],
            {"b": [{"key": "a", "value": 1}, {"key": "b", "value": 2}]},
            [["b", 0], ["b", 1]],
            {"b": "committed"},
        ),
        (
            "initial_manifest_unsorted",
            [begin(list(reversed(two))), chunk(0, a), chunk(1, b), finish()],
            ["started", "staged", "staged", "committed"],
            {"b": [{"key": "a", "value": 1}, {"key": "b", "value": 2}]},
            [["b", 0], ["b", 1]],
            {"b": "committed"},
        ),
        (
            "incomplete_batch_is_invisible",
            [begin(two), chunk(1, b), finish(), restart],
            ["started", "staged", "incomplete", "restarted"],
            {},
            [["b", 1]],
            {"b": "open"},
        ),
        (
            "duplicate_cross_chunk_key",
            [begin(manifest(a, bad)), chunk(0, a), chunk(1, bad), finish()],
            ["started", "staged", "staged", "invalid"],
            {},
            [["b", 0], ["b", 1]],
            {"b": "open"},
        ),
        (
            "duplicate_within_chunk",
            [begin(manifest(a + a)), chunk(0, a + a), finish()],
            ["started", "staged", "invalid"],
            {},
            [["b", 0]],
            {"b": "open"},
        ),
        (
            "retry_after_crash",
            [
                begin(two),
                chunk(1, b),
                chunk(0, a),
                finish(crash=True),
                restart,
                begin(two),
                finish(),
                finish(),
            ],
            [
                "started",
                "staged",
                "staged",
                "crashed",
                "restarted",
                "resumed",
                "committed",
                "committed",
            ],
            {"b": [{"key": "a", "value": 1}, {"key": "b", "value": 2}]},
            [["b", 0], ["b", 1]],
            {"b": "committed"},
        ),
        (
            "immutable_manifest",
            [begin(one), begin(manifest(b)), chunk(0, a), finish()],
            ["started", "conflict", "staged", "committed"],
            {"b": [{"key": "a", "value": 1}]},
            [["b", 0]],
            {"b": "committed"},
        ),
        (
            "duplicate_chunk",
            [begin(one), chunk(0, a), restart, chunk(0, a), finish()],
            ["started", "staged", "restarted", "duplicate", "committed"],
            {"b": [{"key": "a", "value": 1}]},
            [["b", 0]],
            {"b": "committed"},
        ),
        (
            "closed_upload",
            [begin(one), chunk(0, a), finish(), chunk(0, bad), begin(one)],
            ["started", "staged", "committed", "closed", "committed"],
            {"b": [{"key": "a", "value": 1}]},
            [["b", 0]],
            {"b": "committed"},
        ),
        (
            "empty_manifest",
            [begin([]), finish(), restart],
            ["started", "committed", "restarted"],
            {"b": []},
            [],
            {"b": "committed"},
        ),
        (
            "empty_chunk",
            [begin(manifest([])), chunk(0, []), finish()],
            ["started", "staged", "committed"],
            {"b": []},
            [["b", 0]],
            {"b": "committed"},
        ),
        (
            "invalid_index",
            [begin(one), chunk(1, a), finish()],
            ["started", "invalid", "incomplete"],
            {},
            [],
            {"b": "open"},
        ),
        ("unknown_upload", [chunk(0, a), finish()], ["missing", "missing"], {}, [], {}),
        (
            "batch_isolation",
            [
                begin(one),
                begin(one, "other"),
                chunk(0, a, "other"),
                finish(),
                finish("other"),
            ],
            ["started", "started", "staged", "incomplete", "committed"],
            {"other": [{"key": "a", "value": 1}]},
            [["other", 0]],
            {"b": "open", "other": "committed"},
        ),
        (
            "crash_preserves_other_batch_visibility",
            [
                begin(one, "other"),
                chunk(0, a, "other"),
                finish("other"),
                begin(two),
                chunk(0, a),
                chunk(1, b),
                finish(crash=True),
                restart,
            ],
            [
                "started",
                "staged",
                "committed",
                "started",
                "staged",
                "staged",
                "crashed",
                "restarted",
            ],
            {"other": [{"key": "a", "value": 1}]},
            [["b", 0], ["b", 1], ["other", 0]],
            {"b": "open", "other": "committed"},
        ),
        (
            "duplicate_manifest_index",
            [begin([one[0], one[0]])],
            ["invalid"],
            {},
            [],
            {},
        ),
    ]
    wrong_count = [dict(one[0], rows=2)]
    rows.append(
        (
            "count_failure_with_matching_digest",
            [begin(wrong_count), chunk(0, a), finish()],
            ["started", "invalid", "incomplete"],
            {},
            [],
            {"b": "open"},
        )
    )
    for index, (name, commands, results, published, staged, states) in enumerate(rows):
        yield Case(
            name,
            {"commands": commands},
            {
                "results": results,
                "published": published,
                "staged": staged,
                "states": states,
            },
            public=index < 4,
        )
