"""Capacity-limited reservations in a local SQLite service."""
import sqlite3
from contextlib import closing
class InjectedFailure(RuntimeError):pass

def initialize(path, capacities):
    if any(type(v) is not int or v<0 for v in capacities.values()):raise ValueError('invalid capacity')
    with closing(sqlite3.connect(path)) as c:
        c.executescript('CREATE TABLE IF NOT EXISTS machines(id TEXT PRIMARY KEY,capacity INTEGER NOT NULL); CREATE TABLE IF NOT EXISTS reservations(id TEXT PRIMARY KEY,machine_id TEXT NOT NULL,units INTEGER NOT NULL);')
        for m,cap in capacities.items():c.execute('INSERT OR IGNORE INTO machines VALUES (?,?)',(m,cap))
        c.commit()

def reserve(path,request_id,machine_id,units=1,hook=None,fail_after_insert=False):
    if not request_id or type(units) is not int or units<=0:raise ValueError('invalid reservation')
    with closing(sqlite3.connect(path,timeout=5)) as c:
        capacity=c.execute('SELECT capacity FROM machines WHERE id=?',(machine_id,)).fetchone()
        if capacity is None:raise ValueError('unknown machine')
        used=c.execute('SELECT COALESCE(SUM(units),0) FROM reservations WHERE machine_id=?',(machine_id,)).fetchone()[0]
        if hook is not None:hook()
        try:
            c.execute('BEGIN IMMEDIATE')
            prior=c.execute('SELECT machine_id,units FROM reservations WHERE id=?',(request_id,)).fetchone()
            if prior is not None:
                if prior!=(machine_id,units):raise ValueError('request ID conflict')
                c.commit();return True
            if used+units>capacity[0]:c.rollback();return False
            c.execute('INSERT INTO reservations VALUES (?,?,?)',(request_id,machine_id,units))
            if fail_after_insert:raise InjectedFailure('rollback requested')
            c.commit();return True
        except BaseException:c.rollback();raise

def used_units(path,machine_id):
    with closing(sqlite3.connect(path)) as c:return c.execute('SELECT COALESCE(SUM(units),0) FROM reservations WHERE machine_id=?',(machine_id,)).fetchone()[0]

def release(path,request_id):
    with closing(sqlite3.connect(path)) as c:
        count=c.execute('DELETE FROM reservations WHERE id=?',(request_id,)).rowcount;c.commit();return bool(count)
