import json, subprocess, sys
from pathlib import Path

def test_hidden_cli_fixture():
    root=Path(__file__).parent.parent / "data"
    p=subprocess.run([sys.executable,"-m","fabops","--input",str(root/"request.json")],capture_output=True,text=True,timeout=10,check=True)
    assert json.loads(p.stdout)==json.loads((root/"expected.json").read_text())

import pytest
from fabops.checkpoint import initialize,process,inspect,InjectedCrash

def db(tmp_path):
    p=str(tmp_path/'c.db');initialize(p);return p

def events(n=3):return [{'sequence':i,'event_id':f'e{i}','payload':{'v':i}} for i in range(1,n+1)]

@pytest.mark.parametrize('point',['after_output','after_checkpoint'])
@pytest.mark.parametrize('seq',[1,2,3])
def test_every_fault_location(tmp_path,point,seq):
    p=db(tmp_path)
    with pytest.raises(InjectedCrash):process(p,events(),seq,point)
    snapshot=inspect(p);assert snapshot['checkpoint']==seq-1;assert snapshot['outputs']==events()[:seq-1]
    initialize(p);assert process(p,events())['outputs']==events()

def test_repeated_crash_same_event(tmp_path):
    p=db(tmp_path)
    for _ in range(3):
        with pytest.raises(InjectedCrash):process(p,events(),1,'after_checkpoint')
    assert process(p,events())['outputs']==events()

def test_append_new_suffix(tmp_path):
    p=db(tmp_path);process(p,events(2));assert process(p,events(4)[2:])['checkpoint']==4

def test_no_duplicates_after_replay(tmp_path):
    p=db(tmp_path);process(p,events());process(p,events());assert len(inspect(p)['outputs'])==3

def test_invalid_order_atomic(tmp_path):
    p=db(tmp_path)
    with pytest.raises(ValueError):process(p,events()[::-1])
    assert inspect(p)=={'checkpoint':0,'outputs':[]}

def test_invalid_zero_sequence(tmp_path):
    with pytest.raises(ValueError):process(db(tmp_path),[{'sequence':0}])

def test_progress_survives_reinitialize(tmp_path):
    p=db(tmp_path);process(p,events(1));initialize(p);assert inspect(p)['outputs']==events(1)

def test_noncontiguous_ordered_source(tmp_path):
    p=db(tmp_path);rows=[events(1)[0],events(4)[3]];assert process(p,rows)['outputs']==rows
