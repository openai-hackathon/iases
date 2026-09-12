"""The state revision and cached command outcome share one commit."""
import json
import sqlite3
from .canonical import fingerprint, scope_key

def connect(path):
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS states(scope TEXT PRIMARY KEY, revision INTEGER, value TEXT);
        CREATE TABLE IF NOT EXISTS receipts(scope TEXT, key TEXT, fingerprint TEXT, reply TEXT,
            PRIMARY KEY(scope,key));
    """)
    return db

def execute(db, command):
    scope, key = scope_key(command["scope"]), command["key"]
    identity = fingerprint(command)
    previous = db.execute("SELECT fingerprint,reply FROM receipts WHERE key=?", (key,)).fetchone()
    if previous:
        return json.loads(previous[1]) if previous[0] == identity else {"status": "conflict"}
    db.execute("BEGIN IMMEDIATE")
    try:
        current = db.execute("SELECT revision,value FROM states WHERE scope=?", (scope,)).fetchone()
        revision, value = (current[0],json.loads(current[1])) if current else (0,None)
        if command["expected"] != revision:
            reply = dict(status="precondition", revision=revision, value=value)
        else:
            revision += 1
            value = command["value"]
            db.execute("INSERT OR REPLACE INTO states VALUES (?,?,?)", (scope,revision,json.dumps(value)))
            reply = dict(status="applied", revision=revision, value=value)
        if command.get("crash", False):
            raise RuntimeError("interrupted command")
        db.execute("INSERT INTO receipts VALUES (?,?,?,?)", (scope,key,identity,json.dumps(reply)))
        db.commit()
        return reply
    except RuntimeError:
        db.rollback()
        return {"status": "crashed"}
