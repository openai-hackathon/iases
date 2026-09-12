import json, subprocess, sys
from pathlib import Path

def test_hidden_cli_fixture():
    root=Path(__file__).parent.parent / "data"
    p=subprocess.run([sys.executable,"-m","fabops","--input",str(root/"request.json")],capture_output=True,text=True,timeout=10,check=True)
    assert json.loads(p.stdout)==json.loads((root/"expected.json").read_text())

import pytest
from fabops.work_orders import initialize,submit,get_result,count_work_orders,ConflictError
P={'machine_id':'M','reason':'inspect'}
def db(tmp_path):
    p=str(tmp_path/'work.db');initialize(p);return p

def test_conflict_does_not_create_order(tmp_path):
    p=db(tmp_path);submit(p,'k',P)
    with pytest.raises(ConflictError):submit(p,'k',{**P,'reason':'different'})
    assert count_work_orders(p)==1 and get_result(p,'k')['reason']=='inspect'
def test_lost_response_retry(tmp_path):
    p=db(tmp_path)
    with pytest.raises(ConnectionError):submit(p,'k',P,lose_response=True)
    a=get_result(p,'k');assert a is not None;assert submit(p,'k',P)==a;assert count_work_orders(p)==1
def test_reopen_persists_idempotency(tmp_path):
    p=db(tmp_path);a=submit(p,'k',P);initialize(p);assert submit(p,'k',P)==a

def test_payload_key_order_irrelevant(tmp_path):
    p=db(tmp_path);a=submit(p,'k',P);assert submit(p,'k',{'reason':'inspect','machine_id':'M'})==a

def test_concurrent_same_key(tmp_path):
    import threading, concurrent.futures
    p=db(tmp_path);gate=threading.Barrier(2)
    def call():gate.wait(timeout=3);return submit(p,'k',P)
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        futures=[pool.submit(call) for _ in range(2)];a,b=[f.result(timeout=8) for f in futures]
    assert a==b and count_work_orders(p)==1

def test_special_characters_in_key(tmp_path):
    p=db(tmp_path);key="quote';--";a=submit(p,key,P);assert submit(p,key,P)==a

def test_different_machine_conflict(tmp_path):
    p=db(tmp_path);submit(p,'k',P)
    with pytest.raises(ConflictError):submit(p,'k',{**P,'machine_id':'N'})

def test_failed_validation_has_no_effect(tmp_path):
    p=db(tmp_path)
    with pytest.raises(ValueError):submit(p,'k',{'machine_id':'M'})
    assert count_work_orders(p)==0 and get_result(p,'k') is None

def test_empty_key(tmp_path):
    p=db(tmp_path)
    with pytest.raises(ValueError):submit(p,'',P)

def test_distinct_keys_same_payload_distinct_operations(tmp_path):
    p=db(tmp_path);a=submit(p,'a',P);b=submit(p,'b',P);assert a['work_order_id']!=b['work_order_id']

def test_many_replays_one_order(tmp_path):
    p=db(tmp_path);answers=[submit(p,'k',P) for _ in range(8)];assert all(a==answers[0] for a in answers);assert count_work_orders(p)==1
