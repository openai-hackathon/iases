"""SQLite-backed maintenance work orders and operation receipts."""
import json, sqlite3
from contextlib import closing
class ConflictError(ValueError): pass

def initialize(path):
    with closing(sqlite3.connect(path)) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS work_orders(id INTEGER PRIMARY KEY AUTOINCREMENT,machine_id TEXT NOT NULL,reason TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS operations(key TEXT PRIMARY KEY,payload TEXT NOT NULL,result TEXT NOT NULL);
        """)
        c.commit()

def canonical(payload):
    if set(payload)!={'machine_id','reason'} or any(not isinstance(v,str) or not v for v in payload.values()):
        raise ValueError('payload requires nonempty machine_id and reason strings')
    return json.dumps(payload,sort_keys=True,separators=(',',':'))

def submit(path,key,payload,lose_response=False):
    if not isinstance(key,str) or not key:raise ValueError('nonempty key required')
    encoded=canonical(payload)
    with closing(sqlite3.connect(path,timeout=5)) as c:
        try:
            c.execute('BEGIN IMMEDIATE')
            existing=c.execute('SELECT payload,result FROM operations WHERE key=?',(key,)).fetchone()
            if existing is not None:
                if existing[0]!=encoded:raise ConflictError('key already used for a different payload')
                result=json.loads(existing[1])
            else:
                cur=c.execute('INSERT INTO work_orders(machine_id,reason) VALUES (?,?)',(payload['machine_id'],payload['reason']))
                result={'work_order_id':cur.lastrowid,**payload}
                c.execute('INSERT INTO operations(key,payload,result) VALUES (?,?,?)',(key,encoded,json.dumps(result,sort_keys=True)))
            c.commit()
        except BaseException:
            c.rollback();raise
    if lose_response:raise ConnectionError('simulated response lost after durable commit')
    return result

def get_result(path,key):
    with closing(sqlite3.connect(path)) as c:
        row=c.execute('SELECT result FROM operations WHERE key=?',(key,)).fetchone()
        return None if row is None else json.loads(row[0])

def count_work_orders(path):
    with closing(sqlite3.connect(path)) as c:return c.execute('SELECT COUNT(*) FROM work_orders').fetchone()[0]
