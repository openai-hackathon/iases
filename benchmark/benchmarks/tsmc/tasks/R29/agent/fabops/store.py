"""Durable source state is independent of compactable delivery payloads."""
import sqlite3

def connect(path):
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS source(id INTEGER PRIMARY KEY,next INTEGER,total INTEGER,epoch INTEGER,compacted INTEGER);
        INSERT OR IGNORE INTO source VALUES(1,1,0,0,0);
        CREATE TABLE IF NOT EXISTS commands(id TEXT PRIMARY KEY,delta INTEGER,seq INTEGER);
        CREATE TABLE IF NOT EXISTS outbox(seq INTEGER PRIMARY KEY,event TEXT,delta INTEGER);
        CREATE TABLE IF NOT EXISTS lease(id INTEGER PRIMARY KEY,owner TEXT,token INTEGER,expires INTEGER);
        CREATE TABLE IF NOT EXISTS acks(seq INTEGER,consumer TEXT,PRIMARY KEY(seq,consumer));
        CREATE TABLE IF NOT EXISTS consumers(id TEXT PRIMARY KEY,next INTEGER,total INTEGER,trail TEXT);
        INSERT OR IGNORE INTO consumers VALUES('mes',1,0,'[]');
        INSERT OR IGNORE INTO consumers VALUES('quality',1,0,'[]');
        CREATE TABLE IF NOT EXISTS inbox(consumer TEXT,seq INTEGER,event TEXT,delta INTEGER,PRIMARY KEY(consumer,seq));
    """)
    return db

def append(db, command):
    previous = db.execute("SELECT delta,seq FROM commands WHERE id=?", (command["id"],)).fetchone()
    if previous:
        return previous[1] if previous[0] == command["delta"] else "conflict"
    db.execute("BEGIN IMMEDIATE")
    try:
        sequence = db.execute("SELECT next FROM source WHERE id=1").fetchone()[0]
        db.execute("UPDATE source SET next=next+1,total=total+? WHERE id=1", (command["delta"],))
        db.execute("INSERT INTO commands VALUES(?,?,?)", (command["id"],command["delta"],sequence))
        db.commit()
        if command.get("crash", False):
            raise RuntimeError("interrupted append")
        db.execute("INSERT INTO outbox VALUES(?,?,?)", (sequence,command["id"],command["delta"]))
        db.commit()
        return sequence
    except RuntimeError:
        db.rollback()
        return "crashed"
