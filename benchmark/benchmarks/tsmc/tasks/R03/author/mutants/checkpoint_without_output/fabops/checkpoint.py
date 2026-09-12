"""Persist analysis output and resume progress for a replayable event source."""
import json,sqlite3
from contextlib import closing
class InjectedCrash(RuntimeError):pass

def initialize(path):
    with closing(sqlite3.connect(path)) as c:
        c.executescript('CREATE TABLE IF NOT EXISTS checkpoint(id INTEGER PRIMARY KEY,last_seq INTEGER NOT NULL); INSERT OR IGNORE INTO checkpoint VALUES (1,0); CREATE TABLE IF NOT EXISTS outputs(sequence INTEGER PRIMARY KEY,payload TEXT NOT NULL);');c.commit()

def inspect(path):
    with closing(sqlite3.connect(path)) as c:
        cp=c.execute('SELECT last_seq FROM checkpoint WHERE id=1').fetchone()[0]
        rows=c.execute('SELECT payload FROM outputs ORDER BY sequence').fetchall()
        return {'checkpoint':cp,'outputs':[json.loads(x[0]) for x in rows]}

def process(path,events,fail_at=None,crash_point=None):
    previous=0
    for row in events:
        if type(row['sequence']) is not int or row['sequence']<=previous:raise ValueError('strictly increasing positive sequences required')
        previous=row['sequence'];json.dumps(row,allow_nan=False)
    if crash_point not in {None,'after_output','after_checkpoint'}:raise ValueError('unknown crash point')
    for row in events:
        with closing(sqlite3.connect(path,timeout=5)) as c:
            try:
                c.execute('BEGIN IMMEDIATE')
                checkpoint=c.execute('SELECT last_seq FROM checkpoint WHERE id=1').fetchone()[0]
                if row['sequence']<=checkpoint:c.rollback();continue
                pass
                if row['sequence']==fail_at and crash_point=='after_output':raise InjectedCrash(crash_point)
                c.execute('UPDATE checkpoint SET last_seq=? WHERE id=1',(row['sequence'],))
                if row['sequence']==fail_at and crash_point=='after_checkpoint':raise InjectedCrash(crash_point)
                c.commit()
            except BaseException:c.rollback();raise
    return inspect(path)
