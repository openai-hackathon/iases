"""Revision-bound, multi-upload publication with durable tombstones and read sets."""

from dataclasses import replace
import hashlib
import json
from .schema import Case, Change, code
from .hard_infrastructure import ingest_task


def tasks():
    original = ingest_task()
    files = {"fabops/manifest.py": original.files["fabops/manifest.py"]}
    files["fabops/upload.py"] = code('''
        """Bind chunk manifests, dataset scopes and optimistic read sets durably."""
        import json
        import sqlite3
        from .manifest import normalize, canonical, verify

        def connect(path):
            db=sqlite3.connect(path,isolation_level=None)
            db.executescript("""
                CREATE TABLE IF NOT EXISTS uploads(id TEXT PRIMARY KEY,manifest TEXT,status TEXT,scope TEXT,readset TEXT,group_id TEXT);
                CREATE TABLE IF NOT EXISTS chunks(id TEXT,position INTEGER,body TEXT,PRIMARY KEY(id,position));
                CREATE TABLE IF NOT EXISTS published(id TEXT,position INTEGER,body TEXT,PRIMARY KEY(id,position));
                CREATE TABLE IF NOT EXISTS records(scope TEXT,key TEXT,revision INTEGER,value INTEGER,deleted INTEGER,PRIMARY KEY(scope,key));
            """)
            return db

        def begin(db,command):
            try:
                manifest=normalize(command["manifest"])
            except ValueError:
                return "invalid"
            scope=command.get("scope",command["id"])
            readset=canonical(command.get("read_set",{}))
            db.execute("BEGIN IMMEDIATE")
            old=db.execute("SELECT manifest,status,scope,readset FROM uploads WHERE id=?",(command["id"],)).fetchone()
            if old:
                db.commit()
                if (old[0],old[2],old[3]) != (manifest,scope,readset):
                    return "conflict"
                return "committed" if old[1]=="committed" else "resumed"
            db.execute("INSERT INTO uploads VALUES (?,?,?,?,?,NULL)",(command["id"],manifest,"open",scope,readset))
            db.commit()
            return "started"

        def stage(db,command):
            batch,index=command["id"],command["index"]
            upload=db.execute("SELECT manifest,status FROM uploads WHERE id=?",(batch,)).fetchone()
            if upload is None:
                return "missing"
            if upload[1]=="committed":
                return "closed"
            manifest=json.loads(upload[0])
            if not 0<=index<len(manifest):
                return "invalid"
            try:
                body=verify(command["rows"],manifest[index])
            except ValueError:
                return "invalid"
            old=db.execute("SELECT body FROM chunks WHERE id=? AND position=?",(batch,index)).fetchone()
            if old:
                return "duplicate" if old[0]==body else "conflict"
            db.execute("INSERT INTO chunks VALUES (?,?,?)",(batch,index,body))
            return "staged"
    ''')
    files["fabops/revisions.py"] = code('''
        """Check both read-set dependencies and all versioned mutations before publication."""
        def version(db,scope,key):
            row=db.execute("SELECT revision FROM records WHERE scope=? AND key=?",(scope,key)).fetchone()
            return row[0] if row else 0

        def check(db,batches):
            seen=set()
            for scope,readset,rows in batches:
                for row in rows:
                    identity=(scope,row["key"])
                    if identity in seen or row.get("revision",1)<=row.get("expected",0):
                        return "invalid"
                    seen.add(identity)
            for scope,readset,rows in batches:
                for key,expected in readset.items():
                    if version(db,scope,key)!=expected:
                        return "stale"
                for row in rows:
                    if version(db,scope,row["key"])!=row.get("expected",0):
                        return "stale"
            return None

        def apply(db,scope,rows):
            for row in rows:
                db.execute("INSERT OR REPLACE INTO records VALUES (?,?,?,?,?)",
                           (scope,row["key"],row.get("revision",1),row.get("value"),int(row.get("deleted",False))))

        def read(db,scope):
            rows=list(db.execute("SELECT key,revision,value,deleted FROM records WHERE scope=? ORDER BY key",(scope,)))
            return dict(values={key:[rev,value] for key,rev,value,deleted in rows if not deleted},
                        versions={key:rev for key,rev,value,deleted in rows})
    ''')
    files["fabops/publish.py"] = code('''
        """Validate a whole group against one pre-state and commit every participant together."""
        import json
        from .manifest import canonical,verify
        from .revisions import check,apply

        def finish(db,identifiers,crash=False):
            identifiers=sorted(set(identifiers))
            group_id=canonical(identifiers)
            db.execute("BEGIN IMMEDIATE")
            try:
                uploads=[db.execute("SELECT manifest,status,scope,readset,group_id FROM uploads WHERE id=?",(name,)).fetchone() for name in identifiers]
                if any(row is None for row in uploads):
                    db.rollback();return "missing"
                if all(row[1]=="committed" and row[4]==group_id for row in uploads):
                    db.commit();return "committed"
                if any(row[1]=="committed" for row in uploads):
                    db.rollback();return "conflict"
                prepared=[]
                # Completeness of all uploads precedes any content/revision validation.
                staged=[]
                for name,upload in zip(identifiers,uploads):
                    manifest=json.loads(upload[0])
                    chunks=dict(db.execute("SELECT position,body FROM chunks WHERE id=?",(name,)))
                    if set(chunks)!=set(range(len(manifest))):
                        db.rollback();return "incomplete"
                    staged.append((manifest,chunks))
                for upload,(manifest,chunks) in zip(uploads,staged):
                    rows=[]
                    for descriptor in manifest:
                        chunk=json.loads(chunks[descriptor["index"]])
                        verify(chunk,descriptor)
                        rows.extend(chunk)
                    prepared.append((upload[2],json.loads(upload[3]),rows))
                failure=check(db,prepared)
                if failure:
                    db.rollback();return failure
                for name,(scope,_,rows) in zip(identifiers,prepared):
                    apply(db,scope,rows)
                    db.executemany("INSERT OR REPLACE INTO published VALUES (?,?,?)",[(name,i,canonical(row)) for i,row in enumerate(rows)])
                if crash:
                    raise RuntimeError("interrupted group publication")
                for name in identifiers:
                    db.execute("UPDATE uploads SET status='committed',group_id=? WHERE id=?",(group_id,name))
                db.commit();return "committed"
            except ValueError:
                db.rollback();return "invalid"
            except RuntimeError:
                db.rollback();return "crashed"
    ''')
    files["fabops/domain.py"] = code("""
        import json
        import tempfile
        from pathlib import Path
        from .upload import connect,begin,stage
        from .publish import finish
        from .revisions import read

        def run(request):
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/"imports.sqlite"
                db=connect(path);results=[]
                try:
                    for command in request["commands"]:
                        op=command["op"]
                        if op=="begin":result=begin(db,command)
                        elif op=="chunk":result=stage(db,command)
                        elif op=="finish":result=finish(db,[command["id"]],command.get("crash",False))
                        elif op=="finish_group":result=finish(db,command["ids"],command.get("crash",False))
                        elif op=="read":
                            reader=connect(path)
                            try:result=read(reader,command["scope"])
                            finally:reader.close()
                        else:
                            db.close();db=connect(path);result="restarted"
                        results.append(result)
                    published={}
                    for batch,position,body in db.execute("SELECT * FROM published ORDER BY id,position"):
                        published.setdefault(batch,[]).append(json.loads(body))
                    for batch, in db.execute("SELECT id FROM uploads WHERE status='committed'"):
                        published.setdefault(batch,[])
                    staged=[list(row) for row in db.execute("SELECT id,position FROM chunks ORDER BY id,position")]
                    states=dict(db.execute("SELECT id,status FROM uploads ORDER BY id"))
                    return dict(results=results,published=published,staged=staged,states=states)
                finally:
                    db.close()
    """)
    identity = Change(
        "fabops/upload.py",
        "if (old[0],old[2],old[3]) != (manifest,scope,readset):",
        "if old[0] != manifest:",
    )
    readset = Change(
        "fabops/revisions.py",
        "for key,expected in readset.items():",
        "for key,expected in {}.items():",
    )
    revision = Change(
        "fabops/revisions.py",
        'if version(db,scope,row["key"])!=row.get("expected",0):',
        "if False:",
    )
    tombstone = Change(
        "fabops/revisions.py",
        "return row[0] if row else 0",
        'return row[0] if row and not db.execute("SELECT deleted FROM records WHERE scope=? AND key=?",(scope,key)).fetchone()[0] else 0',
    )
    crash = Change(
        "fabops/publish.py",
        "if crash:\n            raise RuntimeError",
        "if crash:\n            db.commit()\n            raise RuntimeError",
    )
    mixed = Change(
        "fabops/publish.py",
        'if any(row[1]=="committed" for row in uploads):',
        "if False:",
    )
    checksum = Change(
        "fabops/manifest.py",
        'if len(rows) != expected["rows"] or digest != expected["sha256"]:',
        'if len(rows) != expected["rows"]:',
    )
    faults = (identity, readset, revision, tombstone, crash, mixed, checksum)
    mutants = {
        name: (fault,)
        for name, fault in zip(
            [
                "manifest_only_identity",
                "read_dependencies_ignored",
                "stale_write_accepted",
                "tombstones_forget_version",
                "group_crash_commits",
                "mixed_committed_group",
                "checksum_ignored",
            ],
            faults,
        )
    }
    mutants["duplicate_cross_upload_key"] = (
        Change(
            "fabops/revisions.py",
            'if identity in seen or row.get("revision",1)<=row.get("expected",0):',
            'if row.get("revision",1)<=row.get("expected",0):',
        ),
    )
    mutants["namespace_ignored"] = (
        Change(
            "fabops/revisions.py", 'identity=(scope,row["key"])', 'identity=row["key"]'
        ),
    )
    contract = original.contract + code("""

        Version 2 adds shared revisioned dataset scopes and atomic group publication.
        begin may specify scope (default upload id) and read_set={key:expected_revision}
        (default {}). These fields are bound immutably together with the normalized chunk
        manifest. Same manifest but different scope/read_set returns conflict even after
        commit. Scopes are independent; staging never changes visible dataset records.

        A chunk row now has key, expected (default 0), revision (default 1), and either
        value (integer) or deleted=true for a tombstone. expected>=0 and revision>=1.
        All fields participate in the canonical chunk digest. A published record version
        starts at 0 for a never-seen key, and retains its last revision when tombstoned.
        Recreating a deleted record therefore requires its tombstone revision as expected.

        finish_group(ids,crash=false) normalizes a nonempty list of upload ids by sorting
        and deduplicating; finish(id) means the singleton group. Check in order: any unknown
        id gives missing; if every member is committed by this SAME normalized group return
        committed without rewriting; any other committed member gives conflict; any missing
        staged chunk gives incomplete; reverify every chunk; duplicate (scope,key) writes
        anywhere in the group or revision<=expected gives invalid; any read_set mismatch
        or row.expected mismatch against the CURRENT pre-transaction dataset gives stale.
        Read sets are checked even for empty uploads and keys not being written. All
        participants compare against the SAME pre-state, never another group's staged
        updates or an earlier write in this group. Disjoint scopes may reuse record keys.

        Only after all checks pass, atomically apply all records/tombstones, publish each
        upload's immutable rows for audit, and mark EVERY upload committed by the group.
        A crash after record/audit writes but before statuses rolls EVERYTHING back, retaining
        staged chunks. Invalid/stale/incomplete/missing/conflict status precedes crash.
        read(scope) uses a separate SQLite connection and returns values={key:[revision,value]}
        for live records and versions={key:revision} INCLUDING tombstones. A later committed
        update changes dataset reads but not an earlier upload's audit rows. restart must
        preserve all versions, read sets, group receipts and unresolved staging on disk.
        Final output remains results,published,staged,states. At most eight uploads, four
        chunks each, twelve rows per chunk and 60 commands. Earlier unversioned uploads
        retain their original behavior in their isolated default scopes.
    """)
    return [
        replace(
            original,
            version="2.0",
            title="Resumed import groups bypass revision read sets and resurrect tombstoned records",
            family="versioned_multi_upload_atomic_publication",
            files=files,
            contract=contract,
            faults=faults,
            mutants=mutants,
            cases=(*original.cases, *cases()),
            difficulty_reason="Bind immutable resumable manifests to shared dataset scopes and read sets, validate all chunks and cross-upload identities against one pre-state, preserve tombstone versions, and publish records, audits and group receipts atomically across restart.",
        )
    ]


def cases():
    def begin(name, rows, scope="fab", read_set=None):
        body = json.dumps(
            rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return dict(
            op="begin",
            id=name,
            scope=scope,
            read_set=read_set or {},
            manifest=[
                dict(
                    index=0,
                    rows=len(rows),
                    sha256=hashlib.sha256(body.encode()).hexdigest(),
                )
            ],
        )

    def chunk(name, rows):
        return dict(op="chunk", id=name, index=0, rows=rows)

    def setup(name, rows, **kw):
        return [begin(name, rows, **kw), chunk(name, rows)]

    def finish(name):
        return dict(op="finish", id=name)

    def group(*names, **kw):
        return dict(op="finish_group", ids=list(names), **kw)

    def read(scope="fab"):
        return dict(op="read", scope=scope)

    restart = dict(op="restart")
    a = [dict(key="k", value=1)]
    b = [dict(key="q", value=2)]

    def case(name, commands, results, published, staged, public=False):
        names = {c["id"] for c in commands if c["op"] == "begin"}
        return Case(
            name,
            dict(commands=commands),
            dict(
                results=results,
                published=published,
                staged=[[n, 0] for n in sorted(staged)],
                states={
                    n: "committed" if n in published else "open" for n in sorted(names)
                },
            ),
            public=public,
        )

    yield case(
        "corrupt_chunk_does_not_survive_restart_into_group",
        [begin("a", a), chunk("a", b), restart] + setup("b", b) + [group("a", "b")],
        ["started", "invalid", "restarted", "started", "staged", "incomplete"],
        {},
        ["b"],
    )
    yield case(
        "atomic_shared_scope_group",
        setup("a", a) + setup("b", b) + [group("b", "a"), read()],
        [
            "started",
            "staged",
            "started",
            "staged",
            "committed",
            dict(values={"k": [1, 1], "q": [1, 2]}, versions={"k": 1, "q": 1}),
        ],
        {"a": a, "b": b},
        ["a", "b"],
        True,
    )
    yield case(
        "group_conflicting_key",
        setup("a", a) + setup("b", a) + [group("a", "b")],
        ["started", "staged", "started", "staged", "invalid"],
        {},
        ["a", "b"],
        True,
    )
    yield case(
        "group_crash_recovery",
        setup("a", a)
        + setup("b", b)
        + [group("a", "b", crash=True), restart, read(), group("a", "b")],
        [
            "started",
            "staged",
            "started",
            "staged",
            "crashed",
            "restarted",
            dict(values={}, versions={}),
            "committed",
        ],
        {"a": a, "b": b},
        ["a", "b"],
        True,
    )
    yield case(
        "read_set_stales_disjoint_write",
        setup("a", a) + setup("b", b, read_set={"k": 0}) + [finish("a"), finish("b")],
        ["started", "staged", "started", "staged", "committed", "stale"],
        {"a": a},
        ["a", "b"],
    )
    newer = [dict(key="k", expected=1, revision=2, value=9)]
    yield case(
        "update_preserves_old_audit",
        setup("a", a)
        + [finish("a")]
        + setup("b", newer)
        + [finish("b"), restart, read()],
        [
            "started",
            "staged",
            "committed",
            "started",
            "staged",
            "committed",
            "restarted",
            dict(values={"k": [2, 9]}, versions={"k": 2}),
        ],
        {"a": a, "b": newer},
        ["a", "b"],
    )
    deleted = [dict(key="k", expected=1, revision=2, deleted=True)]
    yield case(
        "tombstone_prevents_resurrection",
        setup("a", a)
        + [finish("a")]
        + setup("b", deleted)
        + [finish("b"), restart]
        + setup("c", a)
        + [finish("c"), read()],
        [
            "started",
            "staged",
            "committed",
            "started",
            "staged",
            "committed",
            "restarted",
            "started",
            "staged",
            "stale",
            dict(values={}, versions={"k": 2}),
        ],
        {"a": a, "b": deleted},
        ["a", "b", "c"],
    )
    yield case(
        "group_replay_is_idempotent",
        setup("a", a)
        + setup("b", b)
        + [group("a", "b"), restart, group("b", "a", "a")],
        [
            "started",
            "staged",
            "started",
            "staged",
            "committed",
            "restarted",
            "committed",
        ],
        {"a": a, "b": b},
        ["a", "b"],
    )
    yield case(
        "mixed_closed_group_conflicts",
        setup("a", a) + [finish("a")] + setup("b", b) + [group("a", "b")],
        ["started", "staged", "committed", "started", "staged", "conflict"],
        {"a": a},
        ["a", "b"],
    )
    yield case(
        "scope_binding_conflict",
        [begin("a", a), begin("a", a, scope="other")],
        ["started", "conflict"],
        {},
        [],
    )
    yield case(
        "read_set_binding_conflict",
        [begin("a", a), begin("a", a, read_set={"q": 1})],
        ["started", "conflict"],
        {},
        [],
    )
    yield case(
        "disjoint_namespaces_allow_same_key",
        setup("a", a, scope="one") + setup("b", a, scope="two") + [group("a", "b")],
        ["started", "staged", "started", "staged", "committed"],
        {"a": a, "b": a},
        ["a", "b"],
    )
    yield case(
        "all_readsets_use_prestate",
        setup("a", a) + setup("b", b, read_set={"k": 0}) + [group("a", "b")],
        ["started", "staged", "started", "staged", "committed"],
        {"a": a, "b": b},
        ["a", "b"],
    )
    yield case(
        "staged_write_is_not_supply",
        setup("a", a) + setup("b", b, read_set={"k": 1}) + [group("a", "b")],
        ["started", "staged", "started", "staged", "stale"],
        {},
        ["a", "b"],
    )
    yield case(
        "stale_row_expected",
        setup("a", a) + [finish("a")] + setup("b", a) + [finish("b")],
        ["started", "staged", "committed", "started", "staged", "stale"],
        {"a": a},
        ["a", "b"],
    )
    yield case(
        "empty_upload_readset_checked",
        setup("a", [], read_set={"k": 1}) + [finish("a")],
        ["started", "staged", "stale"],
        {},
        ["a"],
    )
