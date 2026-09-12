"""Lease commands and writes share an immediate transaction boundary."""
from .store import allocate
def execute(connection, command):
    connection.execute("BEGIN IMMEDIATE")
    try:
        lease = connection.execute("SELECT owner,token,expires FROM lease WHERE id=1").fetchone()
        if command["op"] == "acquire":
            if lease and command["now"] < lease[2]:
                result = None
            else:
                result = allocate(connection)
                connection.execute("INSERT OR REPLACE INTO lease VALUES (1,?,?,?)",
                                   (command["owner"], result, command["now"] + command["ttl"]))
        elif command["op"] == "retire":
            connection.execute("DELETE FROM lease WHERE id=1")
            result = None
        else:
            result = bool(lease and command["owner"] == lease[0]
                          and command["now"] < lease[2])
            if result:
                connection.execute("UPDATE output SET value=? WHERE id=1", (command["value"],))
        connection.commit()
        return result
    except Exception:
        connection.rollback()
        raise
