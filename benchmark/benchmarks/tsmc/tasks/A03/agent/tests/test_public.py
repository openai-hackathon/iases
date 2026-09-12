import json, subprocess, sys
from pathlib import Path

def test_public_cli_fixture():
    p=subprocess.run([sys.executable,"-m","fabops","--input","data/request.json"],capture_output=True,text=True,timeout=10,check=True)
    assert json.loads(p.stdout)==json.loads(Path("data/expected.json").read_text())

import pytest
from fabops.lineage import impacted_lots

def ts(n):return f'2026-01-15T00:{n:02d}:00Z'
def st(lot='L',machine='M',a=0,b=30):return dict(lot_id=lot,machine_id=machine,enter=ts(a),exit=ts(b))
def ev(id='e',machine='M',a=10,b=20):return dict(event_id=id,machine_id=machine,start=ts(a),end=ts(b))

def test_duplicate_step_not_duplicate_lot(): assert impacted_lots([st(),st()],[ev()])==[{'lot_id':'L','event_ids':['e']}]
def test_one_match(): assert len(impacted_lots([st()],[ev()]))==1
def test_no_overlap(): assert impacted_lots([st(a=30,b=40)],[ev()])==[]
def test_other_machine(): assert impacted_lots([st(machine='N')],[ev()])==[]
