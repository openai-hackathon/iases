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
        if False:
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
