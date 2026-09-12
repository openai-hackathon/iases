import tempfile
from pathlib import Path
from .store import connect
from .package import execute

def run(request):
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory)/"packages.sqlite"
        db=connect(path);results=[]
        try:
            for command in request["commands"]:
                if command["op"]=="restart":
                    db.close();db=connect(path);results.append("restarted")
                else:
                    results.append(execute(db,request["artifacts"],command))
            return dict(results=results,installed=[list(row) for row in db.execute("SELECT id,revision,content FROM installed ORDER BY position")])
        finally:
            db.close()
