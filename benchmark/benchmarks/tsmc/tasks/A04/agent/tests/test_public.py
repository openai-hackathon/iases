import json, subprocess, sys
from pathlib import Path

def test_public_cli_fixture():
    p=subprocess.run([sys.executable,"-m","fabops","--input","data/request.json"],capture_output=True,text=True,timeout=10,check=True)
    assert json.loads(p.stdout)==json.loads(Path("data/expected.json").read_text())

import copy,json,pytest
from fabops.incremental import update,initial_state

def r(n,id=None,t='2026-01-15T00:01:00Z',m='M',v=1):
    return dict(offset=n,event_id=id or f'e{n}',event_time=t,machine_id=m,value=v)
def run(*batches):
    s=initial_state()
    for b in batches:s=update(s,b)
    return s

def test_same_timestamp_distinct_events(): assert run([r(0)],[r(1)])['totals']['M']['count']==2
def test_one_event(): assert run([r(0,v=3)])['totals']['M']['sum']==3
def test_empty_batch(): assert run([])==initial_state()
def test_monotone_time(): assert run([r(0),r(1,t='2026-01-15T00:02:00Z')])['totals']['M']['count']==2
