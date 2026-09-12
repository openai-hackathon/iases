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
