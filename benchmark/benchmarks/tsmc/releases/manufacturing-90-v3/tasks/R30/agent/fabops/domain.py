import tempfile
from pathlib import Path
from .package import connect, install

def run(request):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "package.sqlite"
        db = connect(path)
        results = []
        try:
            for command in request["commands"]:
                if command["op"] == "restart":
                    db.close()
                    db = connect(path)
                    results.append("restarted")
                else:
                    results.append(install(db, request["artifacts"], command["roots"], command.get("crash", False)))
            installed = [list(row) for row in db.execute("SELECT id,revision,content FROM installed ORDER BY position")]
            return dict(results=results, installed=installed)
        finally:
            db.close()
