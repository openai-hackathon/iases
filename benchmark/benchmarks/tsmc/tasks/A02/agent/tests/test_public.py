import json, subprocess, sys
from pathlib import Path

def test_public_cli_fixture():
    p=subprocess.run([sys.executable,"-m","fabops","--input","data/request.json"],capture_output=True,text=True,timeout=10,check=True)
    assert json.loads(p.stdout)==json.loads(Path("data/expected.json").read_text())

import pytest
from fabops.wafer_tests import summarize

def row(id='a',w='w',t='2026-01-15T00:00:00Z',res='PASS',lot='L',valid=True):
    return dict(test_id=id,wafer_id=w,tested_at=t,result=res,lot_id=lot,valid=valid)
def one(rows): return summarize(rows,['L'])[0]

def test_latest_wafer_result():
    r=one([row(res='FAIL'),row('b',t='2026-01-15T00:01:00Z')]);assert r['wafer_count']==1;assert r['passed']==1
def test_no_retest(): assert one([row(),row('b',w='z',res='FAIL')])['pass_ratio']==.5
def test_no_data(): assert one([])['pass_ratio'] is None
def test_invalid_row_excluded(): assert one([row(valid=False)])['wafer_count']==0
