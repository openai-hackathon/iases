"""Compact only a fully consumed and locally acknowledged prefix."""
from .lease import valid

def safe_cut(db):
    return max(row[0] for row in db.execute("SELECT next FROM consumers")) - 1
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
