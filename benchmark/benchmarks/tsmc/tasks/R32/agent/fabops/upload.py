"""Bind chunk manifests, dataset scopes and optimistic read sets durably."""
import json
import sqlite3
from .manifest import normalize, canonical, verify

def connect(path):
    db=sqlite3.connect(path,isolation_level=None)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS uploads(id TEXT PRIMARY KEY,manifest TEXT,status TEXT,scope TEXT,readset TEXT,group_id TEXT);
        CREATE TABLE IF NOT EXISTS chunks(id TEXT,position INTEGER,body TEXT,PRIMARY KEY(id,position));
        CREATE TABLE IF NOT EXISTS published(id TEXT,position INTEGER,body TEXT,PRIMARY KEY(id,position));
        CREATE TABLE IF NOT EXISTS records(scope TEXT,key TEXT,revision INTEGER,value INTEGER,deleted INTEGER,PRIMARY KEY(scope,key));
    """)
    return db

def begin(db,command):
    try:
        manifest=normalize(command["manifest"])
    except ValueError:
        return "invalid"
    scope=command.get("scope",command["id"])
    readset=canonical(command.get("read_set",{}))
    db.execute("BEGIN IMMEDIATE")
    old=db.execute("SELECT manifest,status,scope,readset FROM uploads WHERE id=?",(command["id"],)).fetchone()
    if old:
        db.commit()
        if old[0] != manifest:
            return "conflict"
        return "committed" if old[1]=="committed" else "resumed"
    db.execute("INSERT INTO uploads VALUES (?,?,?,?,?,NULL)",(command["id"],manifest,"open",scope,readset))
    db.commit()
    return "started"

def stage(db,command):
    batch,index=command["id"],command["index"]
    upload=db.execute("SELECT manifest,status FROM uploads WHERE id=?",(batch,)).fetchone()
    if upload is None:
        return "missing"
    if upload[1]=="committed":
        return "closed"
    manifest=json.loads(upload[0])
    if not 0<=index<len(manifest):
        return "invalid"
    try:
        body=verify(command["rows"],manifest[index])
    except ValueError:
        return "invalid"
    old=db.execute("SELECT body FROM chunks WHERE id=? AND position=?",(batch,index)).fetchone()
    if old:
        return "duplicate" if old[0]==body else "conflict"
    db.execute("INSERT INTO chunks VALUES (?,?,?)",(batch,index,body))
    return "staged"
