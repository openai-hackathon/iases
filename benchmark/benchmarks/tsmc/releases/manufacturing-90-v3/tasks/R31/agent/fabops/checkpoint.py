"""Persist unresolved buffers and the last published cut in one checkpoint."""
import copy
import json
import sqlite3

def connect(path):
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE IF NOT EXISTS checkpoint (id INTEGER PRIMARY KEY, payload TEXT)")
    db.commit()
    return db

def save(db, states, published, crash=False):
    durable = copy.deepcopy(states)
    for state in durable.values():
        state["events"] = {key: value for key, value in state["events"].items() if int(key) < state["next"]}
    payload = json.dumps(dict(states=durable, published=published), sort_keys=True)
    db.execute("BEGIN IMMEDIATE")
    try:
        db.execute("INSERT OR REPLACE INTO checkpoint VALUES (1,?)", (payload,))
        db.commit()
        if crash:
            raise RuntimeError("interrupted checkpoint")
        db.commit()
    except RuntimeError:
        db.rollback()
        raise

def load(db):
    row = db.execute("SELECT payload FROM checkpoint WHERE id=1").fetchone()
    data = json.loads(row[0])
    return data["states"], data["published"]
