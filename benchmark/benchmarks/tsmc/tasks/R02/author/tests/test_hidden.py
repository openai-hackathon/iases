import json, subprocess, sys
from pathlib import Path

def test_hidden_cli_fixture():
    root=Path(__file__).parent.parent / "data"
    p=subprocess.run([sys.executable,"-m","fabops","--input",str(root/"request.json")],capture_output=True,text=True,timeout=10,check=True)
    assert json.loads(p.stdout)==json.loads((root/"expected.json").read_text())

import pytest,threading,concurrent.futures
from fabops.reservations import initialize,reserve,used_units,release,InjectedFailure

def db(tmp_path,capacities=None):
    p=str(tmp_path/'r.db');initialize(p,capacities or {'M':1});return p

def race(path,requests):
    gate=threading.Barrier(len(requests))
    with concurrent.futures.ThreadPoolExecutor(len(requests)) as pool:
        fs=[pool.submit(reserve,path,req,m,u,lambda:gate.wait(timeout=3)) for req,m,u in requests]
        return [f.result(timeout=8) for f in fs]

def test_multiunit_race(tmp_path):
    p=db(tmp_path,{'M':3});out=race(p,[('a','M',2),('b','M',2)]);assert out.count(True)==1 and used_units(p,'M')==2

def test_three_contenders_two_slots(tmp_path):
    p=db(tmp_path,{'M':2});out=race(p,[('a','M',1),('b','M',1),('c','M',1)]);assert out.count(True)==2 and used_units(p,'M')==2

def test_different_machine_capacities(tmp_path):
    p=db(tmp_path,{'M':1,'N':1});assert all(race(p,[('a','M',1),('b','N',1)]))

def test_failure_rolls_back(tmp_path):
    p=db(tmp_path)
    with pytest.raises(InjectedFailure):reserve(p,'a','M',fail_after_insert=True)
    assert used_units(p,'M')==0 and reserve(p,'b','M')

def test_repeated_id_idempotent(tmp_path):
    p=db(tmp_path);assert reserve(p,'a','M') and reserve(p,'a','M');assert used_units(p,'M')==1

def test_id_conflict(tmp_path):
    p=db(tmp_path,{'M':3});reserve(p,'a','M')
    with pytest.raises(ValueError):reserve(p,'a','M',2)
    assert used_units(p,'M')==1

def test_unknown_machine(tmp_path):
    with pytest.raises(ValueError):reserve(db(tmp_path),'a','none')

def test_invalid_units(tmp_path):
    p=db(tmp_path)
    for n in [0,-1,True,1.5]:
        with pytest.raises(ValueError):reserve(p,'a','M',n)

def test_zero_capacity(tmp_path):
    p=db(tmp_path,{'M':0});assert not reserve(p,'a','M')

def test_double_release(tmp_path):
    p=db(tmp_path);reserve(p,'a','M');assert release(p,'a');assert not release(p,'a');assert used_units(p,'M')==0

def test_release_restores_capacity(tmp_path):
    p=db(tmp_path);reserve(p,'a','M');release(p,'a');assert reserve(p,'b','M')

def test_deterministic_interleaving_repeated(tmp_path):
    for i in range(4):
        d=tmp_path/str(i);d.mkdir();p=db(d);out=race(p,[('a','M',1),('b','M',1)]);assert sum(out)==1
