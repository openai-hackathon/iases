"""Resolve and prepare against durable floors; publish with a generation CAS."""
import json
from .graph import closure
from .store import generation, replace_package

def execute(db,artifacts,command):
    db.execute("BEGIN IMMEDIATE")
    try:
        op=command["op"]
        if op=="commit":
            ticket=db.execute("SELECT base,body,status FROM tickets WHERE id=?",(command["id"],)).fetchone()
            if ticket is None:
                db.rollback();return "missing"
            if ticket[2]=="committed":
                db.commit();return "installed"
            if False:
                db.rollback();return "stale"
            ordered=json.loads(ticket[1])
            replace_package(db,ordered,command.get("crash",False))
            db.execute("UPDATE tickets SET status='committed' WHERE id=?",(command["id"],))
            result="installed"
        else:
            roots=json.dumps(sorted({tuple(ref) for ref in command["roots"]}),separators=(",",":"))
            if op=="prepare":
                old=db.execute("SELECT roots FROM tickets WHERE id=?",(command["id"],)).fetchone()
                if old:
                    db.commit();return "prepared" if old[0]==roots else "conflict"
            floors=dict(db.execute("SELECT id,revision FROM floors"))
            ordered=closure(artifacts,command["roots"],floors)
            if op=="prepare":
                db.execute("INSERT INTO tickets VALUES (?,?,?,?,?)",(command["id"],roots,generation(db),json.dumps(ordered),"open"))
                if command.get("crash",False):
                    raise RuntimeError("interrupted staging")
                result="prepared"
            else:
                replace_package(db,ordered,command.get("crash",False))
                result="installed"
        db.commit()
        return result
    except ValueError:
        db.rollback();return "invalid"
    except RuntimeError:
        db.rollback();return "crashed"
