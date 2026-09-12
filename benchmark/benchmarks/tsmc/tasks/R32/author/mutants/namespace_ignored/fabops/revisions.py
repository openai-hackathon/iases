"""Check both read-set dependencies and all versioned mutations before publication."""
def version(db,scope,key):
    row=db.execute("SELECT revision FROM records WHERE scope=? AND key=?",(scope,key)).fetchone()
    return row[0] if row else 0

def check(db,batches):
    seen=set()
    for scope,readset,rows in batches:
        for row in rows:
            identity=row["key"]
            if identity in seen or row.get("revision",1)<=row.get("expected",0):
                return "invalid"
            seen.add(identity)
    for scope,readset,rows in batches:
        for key,expected in readset.items():
            if version(db,scope,key)!=expected:
                return "stale"
        for row in rows:
            if version(db,scope,row["key"])!=row.get("expected",0):
                return "stale"
    return None

def apply(db,scope,rows):
    for row in rows:
        db.execute("INSERT OR REPLACE INTO records VALUES (?,?,?,?,?)",
                   (scope,row["key"],row.get("revision",1),row.get("value"),int(row.get("deleted",False))))

def read(db,scope):
    rows=list(db.execute("SELECT key,revision,value,deleted FROM records WHERE scope=? ORDER BY key",(scope,)))
    return dict(values={key:[rev,value] for key,rev,value,deleted in rows if not deleted},
                versions={key:rev for key,rev,value,deleted in rows})
