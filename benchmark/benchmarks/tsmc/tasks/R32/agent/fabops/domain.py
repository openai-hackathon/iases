import json
import tempfile
from pathlib import Path
from .upload import connect,begin,stage
from .publish import finish
from .revisions import read

def run(request):
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory)/"imports.sqlite"
        db=connect(path);results=[]
        try:
            for command in request["commands"]:
                op=command["op"]
                if op=="begin":result=begin(db,command)
                elif op=="chunk":result=stage(db,command)
                elif op=="finish":result=finish(db,[command["id"]],command.get("crash",False))
                elif op=="finish_group":result=finish(db,command["ids"],command.get("crash",False))
                elif op=="read":
                    reader=connect(path)
                    try:result=read(reader,command["scope"])
                    finally:reader.close()
                else:
                    db.close();db=connect(path);result="restarted"
                results.append(result)
            published={}
            for batch,position,body in db.execute("SELECT * FROM published ORDER BY id,position"):
                published.setdefault(batch,[]).append(json.loads(body))
            for batch, in db.execute("SELECT id FROM uploads WHERE status='committed'"):
                published.setdefault(batch,[])
            staged=[list(row) for row in db.execute("SELECT id,position FROM chunks ORDER BY id,position")]
            states=dict(db.execute("SELECT id,status FROM uploads ORDER BY id"))
            return dict(results=results,published=published,staged=staged,states=states)
        finally:
            db.close()
