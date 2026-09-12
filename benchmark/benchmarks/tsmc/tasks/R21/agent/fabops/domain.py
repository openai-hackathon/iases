import json
import tempfile
from pathlib import Path
from .commands import connect, execute
def run(request):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "commands.sqlite"
        db = connect(path)
        results = []
        try:
            for command in request["commands"]:
                if command["op"] == "restart":
                    db.close()
                    db = connect(path)
                    results.append({"status": "restarted"})
                else:
                    results.append(execute(db, command))
            states = [[json.loads(scope), revision, json.loads(value)]
                      for scope, revision, value in db.execute("SELECT * FROM states")]
            states.sort(key=lambda row: row[0])
            return dict(results=results, states=states,
                        receipts=db.execute("SELECT COUNT(*) FROM receipts").fetchone()[0])
        finally:
            db.close()
