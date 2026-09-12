import json, subprocess, sys
from pathlib import Path

def test_public_cli_fixture():
    p=subprocess.run([sys.executable,"-m","fabops","--input","data/request.json"],capture_output=True,text=True,timeout=10,check=True)
    assert json.loads(p.stdout)==json.loads(Path("data/expected.json").read_text())

import pytest,threading,concurrent.futures
from fabops.reservations import initialize,reserve,used_units,release,InjectedFailure

def db(tmp_path,capacities=None):
    p=str(tmp_path/'r.db');initialize(p,capacities or {'M':1});return p

def race(path,requests):
    gate=threading.Barrier(len(requests))
    with concurrent.futures.ThreadPoolExecutor(len(requests)) as pool:
        fs=[pool.submit(reserve,path,req,m,u,lambda:gate.wait(timeout=3)) for req,m,u in requests]
        return [f.result(timeout=8) for f in fs]

def test_simultaneous_capacity_one(tmp_path):
    p=db(tmp_path);results=race(p,[('a','M',1),('b','M',1)]);assert results.count(True)==1;assert used_units(p,'M')==1
def test_single_reservation(tmp_path):
    p=db(tmp_path);assert reserve(p,'a','M');assert used_units(p,'M')==1
def test_sequential_full(tmp_path):
    p=db(tmp_path);reserve(p,'a','M');assert not reserve(p,'b','M')
def test_release(tmp_path):
    p=db(tmp_path);reserve(p,'a','M');assert release(p,'a');assert used_units(p,'M')==0
