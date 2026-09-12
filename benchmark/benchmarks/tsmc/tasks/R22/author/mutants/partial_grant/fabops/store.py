"""Persist resource epochs separately from active grants and output versions."""
import sqlite3

def connect(path, resources):
    db = sqlite3.connect(path, isolation_level=None)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS epochs(resource TEXT PRIMARY KEY, value INTEGER);
        CREATE TABLE IF NOT EXISTS leases(resource TEXT PRIMARY KEY, owner TEXT, token INTEGER, expires INTEGER);
        CREATE TABLE IF NOT EXISTS outputs(resource TEXT PRIMARY KEY, revision INTEGER, value TEXT);
    """)
    for resource in resources:
        db.execute("INSERT OR IGNORE INTO epochs VALUES (?,0)", (resource,))
        db.execute("INSERT OR IGNORE INTO outputs VALUES (?,0,NULL)", (resource,))
    return db

def allocate(db, resource):
    epoch = db.execute("SELECT value FROM epochs WHERE resource=?", (resource,)).fetchone()[0]+1
    db.execute("UPDATE epochs SET value=? WHERE resource=?", (epoch,resource))
    return epoch

def snapshot(db):
    return dict(epochs=dict(db.execute("SELECT resource,value FROM epochs ORDER BY resource")),
                leases={r:[o,t,e] for r,o,t,e in db.execute("SELECT * FROM leases ORDER BY resource")},
                outputs={r:[rev,value] for r,rev,value in db.execute("SELECT * FROM outputs ORDER BY resource")})
