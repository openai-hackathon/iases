"""Reconcile a committed delivery without assuming the ack reached disk."""
import json
from .sink import publish

def deliver(db, event_id, channel, crash="none"):
    row = db.execute("SELECT body FROM events WHERE id=?", (event_id,)).fetchone()
    if row is None:
        return "missing"
    if db.execute("SELECT 1 FROM acks WHERE id=? AND channel=?", (event_id, channel)).fetchone():
        return "acked"
    db.execute("INSERT OR IGNORE INTO acks VALUES (?,?)", (event_id, channel))
    db.commit()
    if crash == "before_sink":
        return "crashed"
    publish(db, channel, json.loads(row[0]))
    if crash == "after_sink":
        return "crashed"
    db.execute("INSERT OR IGNORE INTO acks VALUES (?,?)", (event_id, channel))
    db.commit()
    return "acked"
