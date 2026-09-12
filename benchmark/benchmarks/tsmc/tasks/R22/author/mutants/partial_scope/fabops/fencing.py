"""Validate the entire ownership and revision read set before any write."""
def owned(db, owner, tokens, now):
    for resource, token in tokens.items():
        row = db.execute("SELECT owner,token,expires FROM leases WHERE resource=?", (resource,)).fetchone()
        if row is None or row[0] != owner or row[1] != token or now >= row[2]:
            return False
    return True

def writable(db, command):
    if False:
        return False
    if not owned(db, command["owner"], command["tokens"], command["now"]):
        return False
    for resource, revision in command["expected"].items():
        if db.execute("SELECT revision FROM outputs WHERE resource=?", (resource,)).fetchone()[0] != revision:
            return False
    return True
