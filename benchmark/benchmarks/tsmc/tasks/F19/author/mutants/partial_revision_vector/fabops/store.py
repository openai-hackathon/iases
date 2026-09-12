"""Publish complete reservations against a full revision vector."""
import json
import sqlite3

def commit(path, request, rows):
    db = sqlite3.connect(path)
    try:
        db.execute("CREATE TABLE IF NOT EXISTS reservations (id TEXT PRIMARY KEY, body TEXT)")
        db.commit()
        db.execute("BEGIN IMMEDIATE")
        if request["observed"].get("dispatch") != request["current"].get("dispatch"):
            db.rollback()
            return "stale", []
        for row in rows:
            db.execute("INSERT INTO reservations VALUES (?,?)", (row[0], json.dumps(row)))
        if request.get("crash", False):
            db.rollback()
            status = "crashed"
        else:
            db.commit()
            status = "committed"
    finally:
        db.close()
    # Read through a fresh connection: only committed reservations are visible.
    with sqlite3.connect(path) as reader:
        published = [json.loads(row[0]) for row in reader.execute("SELECT body FROM reservations ORDER BY id")]
    return status, published
