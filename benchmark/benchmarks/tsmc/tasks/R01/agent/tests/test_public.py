import json, subprocess, sys
from pathlib import Path

def test_public_cli_fixture():
    p=subprocess.run([sys.executable,"-m","fabops","--input","data/request.json"],capture_output=True,text=True,timeout=10,check=True)
    assert json.loads(p.stdout)==json.loads(Path("data/expected.json").read_text())

import pytest
from fabops.work_orders import initialize,submit,get_result,count_work_orders,ConflictError
P={'machine_id':'M','reason':'inspect'}
def db(tmp_path):
    p=str(tmp_path/'work.db');initialize(p);return p

def test_repeated_key_same_order(tmp_path):
    p=db(tmp_path);a=submit(p,'k',P);b=submit(p,'k',P);assert a==b and count_work_orders(p)==1
def test_fresh_key(tmp_path):
    p=db(tmp_path);submit(p,'a',P);submit(p,'b',P);assert count_work_orders(p)==2
def test_receipt_lookup(tmp_path):
    p=db(tmp_path);a=submit(p,'a',P);assert get_result(p,'a')==a
def test_unknown_receipt(tmp_path): assert get_result(db(tmp_path),'none') is None
