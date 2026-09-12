"""Backtracking package resolution and generation-bound staged publication."""

from dataclasses import replace
import hashlib
from .schema import Case, Change, code
from .hard_infrastructure import package_task


def tasks():
    original = package_task()
    files = {
        "fabops/graph.py": code('''
            """Resolve a globally compatible, verified, rollback-safe dependency closure."""
            import hashlib

            def closure(artifacts, roots, floors):
                names=sorted({row["id"] for row in artifacts})
                maximum={name:max(row["revision"] for row in artifacts if row["id"]==name) for name in names}
                best,best_rank=None,None
                def ordered(selection):
                    active,done,result=set(),set(),[]
                    def visit(name):
                        if name in active:
                            raise ValueError("dependency cycle")
                        if name in done:
                            return
                        active.add(name)
                        for dep in sorted(selection[name]["requires"]):
                            visit(dep[0])
                        active.remove(name)
                        done.add(name)
                        result.append(selection[name])
                    for root in sorted(roots):
                        visit(root[0])
                    return result
                def search(pending,selection):
                    nonlocal best,best_rank
                    upper=tuple(selection[name]["revision"] if name in selection else maximum[name] for name in names)
                    if best_rank is not None and upper<=best_rank:
                        return
                    if not pending:
                        try:
                            result=ordered(selection)
                        except ValueError:
                            return
                        rank=tuple(selection[name]["revision"] if name in selection else 0 for name in names)
                        if best_rank is None or rank>best_rank:
                            best,best_rank=result,rank
                        return
                    reference,*remaining=sorted(pending)
                    name,low=reference[:2]
                    high=reference[2] if len(reference)==3 else low
                    if name in selection:
                        if low<=selection[name]["revision"]<=high:
                            search(remaining,selection)
                        return
                    candidates=[row for row in artifacts if row["id"]==name and low<=row["revision"]<=high
                                and row["revision"]>=floors.get(name,0) and not row["revoked"]
                                and hashlib.sha256(row["content"].encode()).hexdigest()==row["sha256"]]
                    for row in sorted(candidates,key=lambda row:row["revision"],reverse=True):
                        search(remaining+row["requires"],dict(selection,**{name:row}))
                search(list(roots),{})
                if best is None:
                    raise ValueError("no compatible verified closure")
                return best
        '''),
        "fabops/store.py": code('''
            import sqlite3
            import json

            def connect(path):
                db=sqlite3.connect(path,isolation_level=None)
                db.executescript("""
                    CREATE TABLE IF NOT EXISTS state(id INTEGER PRIMARY KEY, generation INTEGER);
                    INSERT OR IGNORE INTO state VALUES (1,0);
                    CREATE TABLE IF NOT EXISTS installed(position INTEGER PRIMARY KEY,id TEXT,revision INTEGER,content TEXT);
                    CREATE TABLE IF NOT EXISTS floors(id TEXT PRIMARY KEY,revision INTEGER);
                    CREATE TABLE IF NOT EXISTS tickets(id TEXT PRIMARY KEY,roots TEXT,base INTEGER,body TEXT,status TEXT);
                """)
                return db

            def generation(db):
                return db.execute("SELECT generation FROM state WHERE id=1").fetchone()[0]

            def replace_package(db,ordered,crash):
                db.execute("DELETE FROM installed")
                db.executemany("INSERT INTO installed VALUES (?,?,?,?)",[(i,r["id"],r["revision"],r["content"]) for i,r in enumerate(ordered)])
                for row in ordered:
                    db.execute("INSERT INTO floors VALUES (?,?) ON CONFLICT(id) DO UPDATE SET revision=MAX(revision,excluded.revision)",(row["id"],row["revision"]))
                db.execute("UPDATE state SET generation=generation+1 WHERE id=1")
                if crash:
                    raise RuntimeError("interrupted publication")
        '''),
        "fabops/package.py": code('''
            """Resolve and prepare against durable floors; publish with a generation CAS."""
            import json
            from .graph import closure
            from .store import generation, replace_package

            def execute(db,artifacts,command):
                db.execute("BEGIN IMMEDIATE")
                try:
                    op=command["op"]
                    if op=="commit":
                        ticket=db.execute("SELECT base,body,status FROM tickets WHERE id=?",(command["id"],)).fetchone()
                        if ticket is None:
                            db.rollback();return "missing"
                        if ticket[2]=="committed":
                            db.commit();return "installed"
                        if ticket[0]!=generation(db):
                            db.rollback();return "stale"
                        ordered=json.loads(ticket[1])
                        replace_package(db,ordered,command.get("crash",False))
                        db.execute("UPDATE tickets SET status='committed' WHERE id=?",(command["id"],))
                        result="installed"
                    else:
                        roots=json.dumps(sorted({tuple(ref) for ref in command["roots"]}),separators=(",",":"))
                        if op=="prepare":
                            old=db.execute("SELECT roots FROM tickets WHERE id=?",(command["id"],)).fetchone()
                            if old:
                                db.commit();return "prepared" if old[0]==roots else "conflict"
                        floors=dict(db.execute("SELECT id,revision FROM floors"))
                        ordered=closure(artifacts,command["roots"],floors)
                        if op=="prepare":
                            db.execute("INSERT INTO tickets VALUES (?,?,?,?,?)",(command["id"],roots,generation(db),json.dumps(ordered),"open"))
                            if command.get("crash",False):
                                raise RuntimeError("interrupted staging")
                            result="prepared"
                        else:
                            replace_package(db,ordered,command.get("crash",False))
                            result="installed"
                    db.commit()
                    return result
                except ValueError:
                    db.rollback();return "invalid"
                except RuntimeError:
                    db.rollback();return "crashed"
        '''),
        "fabops/domain.py": code("""
            import tempfile
            from pathlib import Path
            from .store import connect
            from .package import execute

            def run(request):
                with tempfile.TemporaryDirectory() as directory:
                    path=Path(directory)/"packages.sqlite"
                    db=connect(path);results=[]
                    try:
                        for command in request["commands"]:
                            if command["op"]=="restart":
                                db.close();db=connect(path);results.append("restarted")
                            else:
                                results.append(execute(db,request["artifacts"],command))
                        return dict(results=results,installed=[list(row) for row in db.execute("SELECT id,revision,content FROM installed ORDER BY position")])
                    finally:
                        db.close()
        """),
    }
    range_fault = Change(
        "fabops/graph.py",
        "high=reference[2] if len(reference)==3 else low",
        'high=max([low]+[row["revision"] for row in artifacts if row["id"]==name])',
    )
    search_fault = Change(
        "fabops/graph.py",
        'search(remaining+row["requires"],dict(selection,**{name:row}))',
        'search(remaining+row["requires"],dict(selection,**{name:row}))\n            break',
    )
    floor_fault = Change(
        "fabops/graph.py", 'row["revision"]>=floors.get(name,0) and ', ""
    )
    cas_fault = Change(
        "fabops/package.py", "if ticket[0]!=generation(db):", "if False:"
    )
    crash_fault = Change(
        "fabops/store.py",
        "if crash:\n        raise RuntimeError",
        "if crash:\n        db.commit()\n        raise RuntimeError",
    )
    checksum = Change(
        "fabops/graph.py",
        'hashlib.sha256(row["content"].encode()).hexdigest()==row["sha256"]',
        "True",
    )
    faults = (range_fault, search_fault, floor_fault, cas_fault, crash_fault, checksum)
    mutants = {
        name: (fault,)
        for name, fault in zip(
            [
                "range_upper_bound_ignored",
                "greedy_highest_revision",
                "rollback_floor_ignored",
                "stale_preparation_commits",
                "partial_crash_commit",
                "digest_not_verified",
            ],
            faults,
        )
    }
    mutants["publication_drops_floor_history"] = (
        Change(
            "fabops/store.py",
            'db.execute("DELETE FROM installed")',
            'db.execute("DELETE FROM installed")\n    db.execute("DELETE FROM floors")',
        ),
    )
    mutants["preparation_advances_floor"] = (
        Change(
            "fabops/package.py",
            'result="prepared"',
            'db.executemany("INSERT OR REPLACE INTO floors VALUES (?,?)",[(r["id"],r["revision"]) for r in ordered])\n                result="prepared"',
        ),
    )
    contract = original.contract + code("""

        Version 2 extends each root/dependency reference to either [id,exact_revision] or
        [id,min_revision,max_revision], inclusive positive bounds. A closure chooses one
        revision per reachable id satisfying ALL incoming constraints. Range choices may
        introduce different transitive dependencies. Search all feasible closures; invalid,
        revoked, corrupt or cyclic choices can be bypassed ONLY when another allowed
        revision has a valid closure. Among valid closures maximize the revision vector
        over all catalog ids sorted lexicographically, using 0 for absent ids. No unrelated
        artifact may be included. Emit the chosen closure by the original sorted-root,
        sorted-reference dependency-first traversal. Exact-pin behavior remains unchanged.

        Maintain durable revision floors per artifact: every successful installation raises
        each included artifact's floor to its installed revision. Never select a revision
        below its floor, even after an empty installation, removal, failed install or restart.
        Floors apply to dependencies as well as roots. Every successful publication,
        including an empty one, increments a global generation initially 0.

        prepare(id,roots,crash=false) resolves and verifies a closure against current floors
        and durably records an immutable ticket containing its closure and current generation,
        without changing installed data or floors. Return prepared, invalid, or crashed.
        Reusing a ticket id with the same root LIST normalized by sorting and deduplication
        returns prepared; different roots return conflict. Existing tickets are not rebased.
        Two-element and three-element reference encodings remain distinct ticket identities.
        A prepare crash rolls back ticket creation. Invalid resolution precedes crash.

        commit(id,crash=false) returns missing if no ticket exists, installed if that ticket
        already committed (with no further generation advance), or stale when its recorded
        generation differs from the current one. Otherwise publish the recorded closure,
        floors, generation and committed ticket status atomically. A crash rolls all four
        back and leaves the ticket retryable. Generation checking must be in the same
        transaction as publication. Direct install also advances generation and can stale
        pending tickets. Existing status checks precede crash handling. Catalog contents
        stay fixed for the request. At most 12 distinct ids and 40 catalog revisions.
        Return the original results/installed shape. All state survives actual SQLite reopen.
    """)
    return [
        replace(
            original,
            version="2.0",
            title="Technical packages greedily resolve ranges and commit stale prepared closures",
            family="range_resolved_rollback_safe_package_cas",
            files=files,
            contract=contract,
            faults=faults,
            mutants=mutants,
            cases=(*original.cases, *cases()),
            difficulty_reason="Replace exact-pin traversal with global revision-range constraint search under integrity, cycle and durable rollback floors, then couple immutable prepared closures to generation-checked atomic publication and crash recovery.",
        )
    ]


def cases():
    def artifact(name, revision=1, requires=(), bad=False):
        content = f"{name}{revision}"
        return dict(
            id=name,
            revision=revision,
            content=content,
            requires=list(requires),
            revoked=False,
            sha256="0" * 64 if bad else hashlib.sha256(content.encode()).hexdigest(),
        )

    def command(op="install", roots=(), **kw):
        return dict(op=op, roots=list(roots), **kw)

    def case(name, artifacts, commands, results, installed, public=False):
        return Case(
            name,
            dict(artifacts=artifacts, commands=commands),
            dict(results=results, installed=[[n, r, f"{n}{r}"] for n, r in installed]),
            public=public,
        )

    catalog = [
        artifact("a", 1, [["b", 1]]),
        artifact("a", 2, [["b", 2]]),
        artifact("b", 1),
        artifact("b", 2),
    ]
    yield case(
        "range_backtracks_shared_pin",
        catalog,
        [command(roots=[["a", 1, 2], ["b", 1]])],
        ["installed"],
        [("b", 1), ("a", 1)],
        True,
    )
    yield case(
        "range_prefers_highest_valid",
        catalog,
        [command(roots=[["a", 1, 2]])],
        ["installed"],
        [("b", 2), ("a", 2)],
        True,
    )
    prepare = command("prepare", [["a", 1]], id="p")
    commit = dict(op="commit", id="p")
    restart = dict(op="restart")
    yield case(
        "intervening_install_stales_ticket",
        catalog,
        [prepare, command(roots=[["b", 2]]), commit],
        ["prepared", "installed", "stale"],
        [("b", 2)],
        True,
    )
    yield case(
        "prepared_crash_retry",
        catalog,
        [prepare, dict(commit, crash=True), restart, commit, commit],
        ["prepared", "crashed", "restarted", "installed", "installed"],
        [("b", 1), ("a", 1)],
    )
    yield case(
        "empty_publication_stales_ticket_across_restart",
        catalog,
        [prepare, command(), restart, dict(commit, crash=True)],
        ["prepared", "installed", "restarted", "stale"],
        [],
    )
    yield case(
        "floor_survives_empty_install",
        catalog,
        [command(roots=[["b", 2]]), command(), restart, command(roots=[["b", 1]])],
        ["installed", "installed", "restarted", "invalid"],
        [],
    )
    yield case(
        "dependency_floor",
        catalog,
        [command(roots=[["b", 2]]), command(roots=[["a", 1]])],
        ["installed", "invalid"],
        [("b", 2)],
    )
    yield case(
        "prepare_does_not_raise_floor",
        catalog,
        [command("prepare", [["b", 2]], id="p"), command(roots=[["b", 1]])],
        ["prepared", "installed"],
        [("b", 1)],
    )
    yield case(
        "prepare_crash_leaves_no_ticket",
        catalog,
        [dict(prepare, crash=True), restart, commit],
        ["crashed", "restarted", "missing"],
        [],
    )
    yield case(
        "ticket_root_conflict",
        catalog,
        [prepare, command("prepare", [["a", 2]], id="p"), commit],
        ["prepared", "conflict", "installed"],
        [("b", 1), ("a", 1)],
    )
    yield case(
        "ticket_duplicate_roots",
        catalog,
        [prepare, command("prepare", [["a", 1], ["a", 1]], id="p"), commit],
        ["prepared", "prepared", "installed"],
        [("b", 1), ("a", 1)],
    )
    yield case(
        "bad_high_revision_falls_back",
        [artifact("a"), artifact("a", 2, bad=True)],
        [command(roots=[["a", 1, 2]])],
        ["installed"],
        [("a", 1)],
    )
    yield case(
        "cyclic_high_revision_falls_back",
        [artifact("a"), artifact("a", 2, [["a", 2]])],
        [command(roots=[["a", 1, 2]])],
        ["installed"],
        [("a", 1)],
    )
    yield case(
        "range_upper_bound",
        [artifact("a"), artifact("a", 2), artifact("a", 3)],
        [command(roots=[["a", 1, 2]])],
        ["installed"],
        [("a", 2)],
    )
    yield case(
        "crash_floor_rolls_back",
        catalog,
        [command(roots=[["b", 2]], crash=True), restart, command(roots=[["b", 1]])],
        ["crashed", "restarted", "installed"],
        [("b", 1)],
    )
    yield case(
        "global_revision_vector_beats_root_greed",
        [
            artifact("a", 1),
            artifact("a", 2),
            artifact("z", 1, [["a", 2]]),
            artifact("z", 2, [["a", 1]]),
        ],
        [command(roots=[["z", 1, 2]])],
        ["installed"],
        [("a", 2), ("z", 1)],
    )
    yield case(
        "twelve_independent_ranges",
        [artifact(f"p{i:02d}", revision) for i in range(12) for revision in [1, 2, 3]],
        [command(roots=[[f"p{i:02d}", 1, 3] for i in range(12)])],
        ["installed"],
        [(f"p{i:02d}", 3) for i in range(12)],
    )
