"""A sink commit cannot be rolled back by a missing local acknowledgement."""
from .consumer import accept
from .lease import valid

def deliver(db, command):
    if not valid(db, command):
        return "fenced"
    sequence, consumer = command["seq"], command["consumer"]
    event = db.execute("SELECT event,delta FROM outbox WHERE seq=?", (sequence,)).fetchone()
    if event is None:
        return "missing"
    if db.execute("SELECT 1 FROM acks WHERE seq=? AND consumer=?", (sequence,consumer)).fetchone():
        return "acked"
    if command.get("crash") == "before_sink":
        return "crashed"
    accept(db, consumer, sequence, *event)
    if command.get("crash") == "after_sink":
        return "crashed"
    with db:
        db.execute("INSERT OR IGNORE INTO acks VALUES(?,?)", (sequence,consumer))
    return "acked"
