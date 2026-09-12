import json
import tempfile
from pathlib import Path
from .store import connect, append
from .lease import acquire, valid
from .relay import deliver
from .retention import compact

def run(request):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "outbox.sqlite"
        db = connect(path)
        results = []
        try:
            for command in request["commands"]:
                op = command["op"]
                if op == "append":
                    result = append(db, command)
                elif op == "acquire":
                    result = acquire(db, command)
                elif op == "deliver":
                    result = deliver(db, command)
                elif op == "compact":
                    result = compact(db, command)
                elif op == "retire":
                    result = "fenced"
                    if valid(db, command):
                        with db:
                            db.execute("DELETE FROM lease")
                        result = "retired"
                else:
                    db.close()
                    db = connect(path)
                    result = "restarted"
                results.append(result)
            next_sequence,total,epoch,cut = db.execute("SELECT next,total,epoch,compacted FROM source WHERE id=1").fetchone()
            lease = db.execute("SELECT owner,token,expires FROM lease WHERE id=1").fetchone()
            consumers = {}
            for name,frontier,value,trail in db.execute("SELECT * FROM consumers"):
                consumers[name] = dict(next=frontier,total=value,trail=json.loads(trail),
                    buffered=[row[0] for row in db.execute("SELECT seq FROM inbox WHERE consumer=? ORDER BY seq", (name,))])
            return dict(results=results,next_sequence=next_sequence,total=total,epoch=epoch,compacted=cut,
                        lease=list(lease) if lease else None,consumers=consumers,
                        retained=[row[0] for row in db.execute("SELECT seq FROM outbox ORDER BY seq")],
                        acks=[list(row) for row in db.execute("SELECT seq,consumer FROM acks ORDER BY seq,consumer")],
                        commands=db.execute("SELECT COUNT(*) FROM commands").fetchone()[0])
        finally:
            db.close()
