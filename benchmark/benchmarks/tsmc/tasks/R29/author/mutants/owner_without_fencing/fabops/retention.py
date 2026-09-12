"""Compact only a fully consumed and locally acknowledged prefix."""
from .lease import valid

def safe_cut(db):
    cut, next_sequence = db.execute("SELECT compacted,next FROM source WHERE id=1").fetchone()
    frontier = min(row[0] for row in db.execute("SELECT next FROM consumers"))
    while cut + 1 < min(frontier, next_sequence):
        acknowledged = db.execute("SELECT COUNT(*) FROM acks WHERE seq=?", (cut+1,)).fetchone()[0]
        if acknowledged != 2:
            break
        cut += 1
    return cut
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
