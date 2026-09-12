import json, subprocess, sys
from pathlib import Path

def test_hidden_cli_fixture():
    root=Path(__file__).parent.parent / "data"
    p=subprocess.run([sys.executable,"-m","fabops","--input",str(root/"request.json")],capture_output=True,text=True,timeout=10,check=True)
    assert json.loads(p.stdout)==json.loads((root/"expected.json").read_text())

import copy, pytest
from fabops.machine_events import reduce_events, ConflictError

def ev(n,s="AVAILABLE",m="M"):
    return dict(machine_id=m,sequence=n,new_state=s,event_id=f"{m}-{n}")

def test_replay_no_effect(): assert reduce_events([ev(1),ev(1)])==reduce_events([ev(1)])
def test_equal_sequence_conflict():
    with pytest.raises(ConflictError):reduce_events([ev(5),ev(5,"LOCKED")])
def test_initial_state_protected():
    initial={'M':{'sequence':20,'state':'LOCKED'}}
    assert reduce_events([ev(19)],initial)==initial
def test_multiple_machines_out_of_order():
    rows=[ev(5,'LOCKED'),ev(8,'BUSY','N'),ev(2),ev(7,'AVAILABLE','N')]
    assert reduce_events(rows)=={'M':{'sequence':5,'state':'LOCKED'},'N':{'sequence':8,'state':'BUSY'}}
def test_clock_not_ordering_key():
    x=ev(8,'LOCKED');x['received_at']='2020';y=ev(7);y['received_at']='2030'
    assert reduce_events([x,y])['M']['sequence']==8
def test_zero_sequence(): assert reduce_events([ev(0)])['M']['sequence']==0
def test_negative_sequence_rejected():
    with pytest.raises(ValueError):reduce_events([ev(-1)])
def test_bad_state_rejected():
    with pytest.raises(ValueError):reduce_events([ev(0,'BOGUS')])
def test_inputs_unchanged_on_conflict():
    initial={'M':{'sequence':1,'state':'AVAILABLE'}};before=copy.deepcopy(initial)
    with pytest.raises(ConflictError):reduce_events([ev(1,'LOCKED')],initial)
    assert initial==before
def test_batch_incremental_equivalence():
    a=[ev(9,'LOCKED'),ev(2)];b=[ev(8,'BUSY'),ev(10,'MAINTENANCE')]
    assert reduce_events(a+b)==reduce_events(b,reduce_events(a))
def test_permutation_unique_sequences():
    import random
    rows=[ev(n,'BUSY' if n==29 else 'AVAILABLE') for n in range(30)]
    random.Random(902).shuffle(rows);assert reduce_events(rows)['M']=={'sequence':29,'state':'BUSY'}
def test_stale_conflict_not_current_is_ignored():
    assert reduce_events([ev(3,'LOCKED'),ev(1),ev(1,'BUSY')])['M']['sequence']==3
