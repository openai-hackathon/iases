"""Grant durable fencing epochs, including after the active lease is retired."""
def valid(db, command):
    lease = db.execute("SELECT owner,token,expires FROM lease WHERE id=1").fetchone()
    return bool(lease and command["owner"] == lease[0]
                and command["token"] == lease[1] and command["now"] <= lease[2])

def acquire(db, command):
    lease = db.execute("SELECT expires FROM lease WHERE id=1").fetchone()
    if lease and command["now"] < lease[0]:
        return None
    with db:
        token = db.execute("SELECT epoch FROM source WHERE id=1").fetchone()[0] + 1
        db.execute("UPDATE source SET epoch=? WHERE id=1", (token,))
        db.execute("INSERT OR REPLACE INTO lease VALUES(1,?,?,?)",
                   (command["owner"],token,command["now"]+command["ttl"]))
    return token
