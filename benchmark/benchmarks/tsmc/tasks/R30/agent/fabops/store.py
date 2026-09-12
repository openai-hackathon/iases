import sqlite3
import json

def connect(path):
    db=sqlite3.connect(path,isolation_level=None)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS state(id INTEGER PRIMARY KEY, generation INTEGER);
        INSERT OR IGNORE INTO state VALUES (1,0);
        CREATE TABLE IF NOT EXISTS installed(position INTEGER PRIMARY KEY,id TEXT,revision INTEGER,content TEXT);
        CREATE TABLE IF NOT EXISTS floors(id TEXT PRIMARY KEY,revision INTEGER);
        CREATE TABLE IF NOT EXISTS tickets(id TEXT PRIMARY KEY,roots TEXT,base INTEGER,body TEXT,status TEXT);
    """)
    return db

def generation(db):
    return db.execute("SELECT generation FROM state WHERE id=1").fetchone()[0]

def replace_package(db,ordered,crash):
    db.execute("DELETE FROM installed")
    db.executemany("INSERT INTO installed VALUES (?,?,?,?)",[(i,r["id"],r["revision"],r["content"]) for i,r in enumerate(ordered)])
    for row in ordered:
        db.execute("INSERT INTO floors VALUES (?,?) ON CONFLICT(id) DO UPDATE SET revision=MAX(revision,excluded.revision)",(row["id"],row["revision"]))
    db.execute("UPDATE state SET generation=generation+1 WHERE id=1")
    if crash:
        db.commit()
        raise RuntimeError("interrupted publication")
