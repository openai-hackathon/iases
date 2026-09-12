import tempfile
from pathlib import Path
from .store import connect, snapshot
from .lease import execute

def run(request):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)/"grants.sqlite"
        db = connect(path,request["resources"])
        results = []
        try:
            for command in request["commands"]:
                if command["op"] == "restart":
                    db.close()
                    db = connect(path,request["resources"])
                    results.append("restarted")
                elif command["op"] == "read":
                    reader = connect(path,request["resources"])
                    try:
                        results.append(snapshot(reader))
                    finally:
                        reader.close()
                else:
                    results.append(execute(db,command))
            return dict(results=results,**snapshot(db))
        finally:
            db.close()
