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
            seen = set()
            chunk = json.loads(chunks[expected["index"]])
            verify(chunk, expected)
            for row in chunk:
                if row["key"] in seen:
                    raise ValueError("duplicate record identity across batch")
                seen.add(row["key"])
                rows.append(row)
        db.executemany("INSERT OR REPLACE INTO published VALUES (?,?,?)",
                       [(batch, index, canonical(row)) for index, row in enumerate(rows)])
        db.commit()
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
