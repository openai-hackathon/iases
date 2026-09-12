"""Stage validated chunks durably without exposing an unfinished batch."""
import json
import sqlite3
from .manifest import normalize, verify

def connect(path):
    db = sqlite3.connect(path, isolation_level=None)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS uploads (id TEXT PRIMARY KEY, manifest TEXT, status TEXT);
        CREATE TABLE IF NOT EXISTS chunks (id TEXT, position INTEGER, body TEXT, PRIMARY KEY(id,position));
        CREATE TABLE IF NOT EXISTS published (id TEXT, position INTEGER, body TEXT, PRIMARY KEY(id,position));
    """)
    return db

def begin(db, command):
    try:
        manifest = normalize(command["manifest"])
    except ValueError:
        return "invalid"
    old = db.execute("SELECT manifest,status FROM uploads WHERE id=?", (command["id"],)).fetchone()
    if old:
        if old[0] != manifest:
            return "conflict"
        return "committed" if old[1] == "committed" else "resumed"
    db.execute("INSERT INTO uploads VALUES (?,?,?)", (command["id"], manifest, "open"))
    return "started"

def stage(db, command):
    batch, index = command["id"], command["index"]
    upload = db.execute("SELECT manifest,status FROM uploads WHERE id=?", (batch,)).fetchone()
    if upload is None:
        return "missing"
    if upload[1] == "committed":
        return "closed"
    manifest = json.loads(upload[0])
    if index < 0 or index >= len(manifest):
        return "invalid"
    try:
        body = verify(command["rows"], manifest[index])
    except ValueError:
        return "invalid"
    old = db.execute("SELECT body FROM chunks WHERE id=? AND position=?", (batch, index)).fetchone()
    if old:
        return "duplicate" if old[0] == body else "conflict"
    db.execute("INSERT INTO chunks VALUES (?,?,?)", (batch, index, body))
    return "staged"
