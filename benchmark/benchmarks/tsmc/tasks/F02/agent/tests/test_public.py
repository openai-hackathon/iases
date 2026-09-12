import json, subprocess, sys
from pathlib import Path

def test_public_cli_fixture():
    p=subprocess.run([sys.executable,"-m","fabops","--input","data/request.json"],capture_output=True,text=True,timeout=10,check=True)
    assert json.loads(p.stdout)==json.loads(Path("data/expected.json").read_text())

from fabops.qualifications import Registry, ConflictError
import pytest

def rec(v=1,ok=True,m="M",p="P",s="S"):
    return dict(machine_id=m,product_id=p,step_id=s,version=v,valid=ok)
def ask(r,m="M",p="P",s="S"): return r.allowed(m,p,s)

def test_initial_allowed(): assert ask(Registry([rec()]))
def test_cached_revocation():
    r=Registry([rec()]);assert ask(r);r.apply(rec(2,False));assert not ask(r)
def test_missing_false(): assert not ask(Registry())
def test_stale_update_ignored():
    r=Registry([rec(3,False)]);r.apply(rec(2,True));assert not ask(r)
