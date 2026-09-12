import json, subprocess, sys
from pathlib import Path

def test_public_cli_fixture():
    p=subprocess.run([sys.executable,"-m","fabops","--input","data/request.json"],capture_output=True,text=True,timeout=10,check=True)
    assert json.loads(p.stdout)==json.loads(Path("data/expected.json").read_text())

import pytest
from fabops.checkpoint import initialize,process,inspect,InjectedCrash

def db(tmp_path):
    p=str(tmp_path/'c.db');initialize(p);return p

def events(n=3):return [{'sequence':i,'event_id':f'e{i}','payload':{'v':i}} for i in range(1,n+1)]

def test_crash_then_resume_no_loss(tmp_path):
    p=db(tmp_path)
    with pytest.raises(InjectedCrash):process(p,events(),2,'after_checkpoint')
    assert process(p,events())['outputs']==events()

def test_normal(tmp_path):
    p=db(tmp_path);assert process(p,events())=={'checkpoint':3,'outputs':events()}

def test_replay(tmp_path):
    p=db(tmp_path);process(p,events());assert process(p,events())['outputs']==events()

def test_empty(tmp_path): assert process(db(tmp_path),[])=={'checkpoint':0,'outputs':[]}
