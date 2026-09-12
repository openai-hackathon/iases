import json, subprocess, sys
from pathlib import Path

def test_public_cli_fixture():
    p=subprocess.run([sys.executable,"-m","fabops","--input","data/request.json"],capture_output=True,text=True,timeout=10,check=True)
    assert json.loads(p.stdout)==json.loads(Path("data/expected.json").read_text())

import copy, pytest
from fabops.machine_events import reduce_events, ConflictError

def ev(n,s="AVAILABLE",m="M"):
    return dict(machine_id=m,sequence=n,new_state=s,event_id=f"{m}-{n}")

def test_late_older_event(): assert reduce_events([ev(3,"LOCKED"),ev(2)])['M']['state']=='LOCKED'
def test_in_order(): assert reduce_events([ev(1),ev(2,"BUSY")])['M']['sequence']==2
def test_empty(): assert reduce_events([])=={}
def test_independent_machines(): assert len(reduce_events([ev(1),ev(1,m='N')]))==2
