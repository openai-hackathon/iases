import json, subprocess, sys
from pathlib import Path

def test_hidden_cli_fixture():
    root=Path(__file__).parent.parent / "data"
    p=subprocess.run([sys.executable,"-m","fabops","--input",str(root/"request.json")],capture_output=True,text=True,timeout=10,check=True)
    assert json.loads(p.stdout)==json.loads((root/"expected.json").read_text())

import pytest
from fabops.lineage import impacted_lots

def ts(n):return f'2026-01-15T00:{n:02d}:00Z'
def st(lot='L',machine='M',a=0,b=30):return dict(lot_id=lot,machine_id=machine,enter=ts(a),exit=ts(b))
def ev(id='e',machine='M',a=10,b=20):return dict(event_id=id,machine_id=machine,start=ts(a),end=ts(b))

def test_multiple_evidence_ids(): assert impacted_lots([st()],[ev('b'),ev('a')])==[{'lot_id':'L','event_ids':['a','b']}]
def test_duplicate_events_invariant(): assert impacted_lots([st()],[ev(),ev()])==impacted_lots([st()],[ev()])
def test_lot_sort_and_evidence_sort():
    r=impacted_lots([st('Z'),st('A')],[ev('z'),ev('b')]);assert r==[{'lot_id':x,'event_ids':['b','z']} for x in ['A','Z']]
def test_half_open_boundary(): assert impacted_lots([st(a=20,b=30)],[ev(a=10,b=20)])==[]
def test_zero_length_step(): assert impacted_lots([st(a=15,b=15)],[ev()])==[]
def test_zero_length_event(): assert impacted_lots([st()],[ev(a=15,b=15)])==[]
def test_time_zone_equivalence():
    e=ev();e.update(start='2026-01-15T08:10:00+08:00',end='2026-01-15T08:20:00+08:00')
    assert impacted_lots([st()],[e])==[{'lot_id':'L','event_ids':['e']}]
def test_reversed_interval():
    with pytest.raises(ValueError):impacted_lots([st(a=30,b=0)],[ev()])
def test_empty_inputs(): assert impacted_lots([],[])==[]
def test_same_lot_multiple_steps():
    r=impacted_lots([st(),st(a=30,b=50)],[ev('x'),ev('y',a=40,b=45)]);assert r==[{'lot_id':'L','event_ids':['x','y']}]
def test_no_false_evidence():
    r=impacted_lots([st()],[ev('in'),ev('out',a=40,b=50)]);assert r[0]['event_ids']==['in']
def test_permutation_invariant():
    steps=[st(),st('B'),st()];events=[ev('b'),ev('a')]
    assert impacted_lots(steps,events)==impacted_lots(steps[::-1],events[::-1])
