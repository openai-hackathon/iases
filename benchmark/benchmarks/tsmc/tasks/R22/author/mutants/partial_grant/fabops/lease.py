"""One immediate transaction owns a whole grant, renewal, release or write."""
from .store import allocate
from .fencing import owned, writable

def execute(db, command):
    db.execute("BEGIN IMMEDIATE")
    try:
        op, now = command["op"], command["now"]
        if op == "acquire":
            resources = sorted(set(command["resources"]))
            busy = [db.execute("SELECT expires FROM leases WHERE resource=?", (r,)).fetchone() for r in resources]
            if all(row and now < row[0] for row in busy):
                db.rollback()
                return None
            result = {}
            for resource in resources:
                result[resource] = allocate(db, resource)
                db.execute("INSERT OR REPLACE INTO leases VALUES (?,?,?,?)",
                           (resource,command["owner"],result[resource],now+command["ttl"]))
        elif op in ("renew", "release"):
            result = owned(db,command["owner"],command["tokens"],now)
            if not result:
                db.rollback()
                return False
            for resource in command["tokens"]:
                if op == "renew":
                    db.execute("UPDATE leases SET expires=MAX(expires,?) WHERE resource=?",(now+command["ttl"],resource))
                else:
                    db.execute("DELETE FROM leases WHERE resource=?",(resource,))
        else:
            result = writable(db,command)
            if not result:
                db.rollback()
                return False
            for resource,value in sorted(command["updates"].items()):
                db.execute("UPDATE outputs SET revision=revision+1,value=? WHERE resource=?",(value,resource))
        if command.get("crash",False):
            raise RuntimeError("interrupted before transaction commit")
        db.commit()
        return result
    except RuntimeError:
        db.rollback()
        return "crashed"
    except Exception:
        db.rollback()
        raise
