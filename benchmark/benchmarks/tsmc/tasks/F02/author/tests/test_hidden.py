import json, subprocess, sys
from pathlib import Path

def test_hidden_cli_fixture():
    root=Path(__file__).parent.parent / "data"
    p=subprocess.run([sys.executable,"-m","fabops","--input",str(root/"request.json")],capture_output=True,text=True,timeout=10,check=True)
    assert json.loads(p.stdout)==json.loads((root/"expected.json").read_text())

from fabops.qualifications import Registry, ConflictError
import pytest

def rec(v=1,ok=True,m="M",p="P",s="S"):
    return dict(machine_id=m,product_id=p,step_id=s,version=v,valid=ok)
def ask(r,m="M",p="P",s="S"): return r.allowed(m,p,s)

def test_cached_upgrade():
    r=Registry([rec(1,False)]);assert not ask(r);r.apply(rec(2,True));assert ask(r)
def test_negative_cache_refresh():
    r=Registry();assert not ask(r);r.apply(rec(0));assert ask(r)
def test_revoke_after_many_reads():
    r=Registry([rec()]);assert all(ask(r) for _ in range(8));r.apply(rec(100,False));assert not ask(r)
def test_independent_keys():
    r=Registry([rec(),rec(m="N")]);assert ask(r) and ask(r,"N");r.apply(rec(2,False));assert not ask(r);assert ask(r,"N")
def test_product_isolation():
    r=Registry([rec(p="Q",ok=False),rec()]);assert ask(r);assert not ask(r,p="Q")
def test_step_isolation():
    r=Registry([rec(s="T",ok=False),rec()]);assert ask(r);assert not ask(r,s="T")
def test_same_version_conflict_atomic():
    r=Registry([rec()]);ask(r)
    with pytest.raises(ConflictError):r.apply(rec(1,False))
    assert ask(r)
def test_same_version_replay():
    r=Registry([rec()]);assert r.apply(rec()) is False;assert ask(r)
def test_old_version_cannot_restore_revoked():
    r=Registry([rec(8,False)]);r.apply(rec(7));assert not ask(r)
def test_event_defensive_copy():
    e=rec();r=Registry([e]);e["valid"]=False;assert ask(r)
def test_invalid_version():
    with pytest.raises(ValueError):Registry([rec(-1)])
def test_generated_version_transitions():
    r=Registry()
    for v in range(30):
        r.apply(rec(v, v%3==0));assert ask(r)==(v%3==0)
