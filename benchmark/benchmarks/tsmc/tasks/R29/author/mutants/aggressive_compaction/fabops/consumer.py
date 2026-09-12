"""Buffer durable gaps and apply exactly one contiguous stream prefix."""
import json

def drain(db, consumer):
    next_sequence, total, trail = db.execute(
        "SELECT next,total,trail FROM consumers WHERE id=?", (consumer,)).fetchone()
    trail = json.loads(trail)
    while True:
        item = db.execute("SELECT event,delta FROM inbox WHERE consumer=? AND seq=?",
                          (consumer,next_sequence)).fetchone()
        if item is None:
            break
        event, delta = item
        total += delta
        trail.append(event)
        db.execute("DELETE FROM inbox WHERE consumer=? AND seq=?", (consumer,next_sequence))
        next_sequence += 1
    db.execute("UPDATE consumers SET next=?,total=?,trail=? WHERE id=?",
               (next_sequence,total,json.dumps(trail),consumer))
def accept(db, consumer, sequence, event, delta):
    db.execute("BEGIN IMMEDIATE")
    try:
        frontier = db.execute("SELECT next FROM consumers WHERE id=?", (consumer,)).fetchone()[0]
        if sequence >= frontier:
            db.execute("INSERT OR IGNORE INTO inbox VALUES(?,?,?,?)", (consumer,sequence,event,delta))
        drain(db, consumer)
        db.commit()
    except Exception:
        db.rollback()
        raise
