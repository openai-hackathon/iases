"""Persist the publication intent and each channel acknowledgement."""
import json
import sqlite3

CHANNELS = ("vds", "qdr", "tdp")

def connect(path):
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, body TEXT);
        CREATE TABLE IF NOT EXISTS acks (id TEXT, channel TEXT, PRIMARY KEY(id,channel));
        CREATE TABLE IF NOT EXISTS receipts (id TEXT, channel TEXT);
        CREATE TABLE IF NOT EXISTS projection (channel TEXT, artifact TEXT, revision INTEGER,
            payload TEXT, PRIMARY KEY(channel,artifact));
    """)
    return db

def enqueue(db, command):
    event = command["event"]
    body = json.dumps(event, sort_keys=True, separators=(",", ":"))
    old = db.execute("SELECT body FROM events WHERE id=?", (event["id"],)).fetchone()
    if old:
        return "duplicate" if old[0] == body else "conflict"
    db.execute("BEGIN IMMEDIATE")
    try:
        db.execute("INSERT INTO events VALUES (?,?)", (event["id"], body))
        if command.get("crash", False):
            raise RuntimeError("interrupted enqueue")
        db.commit()
        return "queued"
    except RuntimeError:
        db.rollback()
        return "crashed"

def pending(db):
    return [[event, channel] for (event,) in db.execute("SELECT id FROM events ORDER BY id")
            for channel in CHANNELS if not db.execute(
                "SELECT 1 FROM acks WHERE id=? AND channel=?", (event, channel)).fetchone()]
