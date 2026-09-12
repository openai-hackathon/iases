"""Verify every linked object and atomically replace the installed manifest."""
import hashlib
import sqlite3
from .graph import closure

def connect(path):
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE IF NOT EXISTS installed (position INTEGER PRIMARY KEY, id TEXT, revision INTEGER, content TEXT)")
    db.commit()
    return db

def install(db, artifacts, roots, crash=False):
    try:
        ordered = closure(artifacts, roots)
        for row in ordered:
            if [row["id"], row["revision"]] not in roots:
                continue
            if hashlib.sha256(row["content"].encode("utf-8")).hexdigest() != row["sha256"]:
                raise ValueError("content digest mismatch")
    except ValueError:
        return "invalid"
    db.execute("BEGIN IMMEDIATE")
    try:
        db.execute("DELETE FROM installed")
        if crash:
            raise RuntimeError("interrupted package replacement")
        db.executemany("INSERT INTO installed VALUES (?,?,?,?)", [
            (index, row["id"], row["revision"], row["content"])
            for index, row in enumerate(ordered)])
        db.commit()
        return "installed"
    except RuntimeError:
        db.rollback()
        return "crashed"
