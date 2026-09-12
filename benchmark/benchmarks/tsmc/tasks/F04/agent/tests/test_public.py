import json, subprocess, sys
from pathlib import Path

def test_public_cli_fixture():
    p=subprocess.run([sys.executable,"-m","fabops","--input","data/request.json"],capture_output=True,text=True,timeout=10,check=True)
    assert json.loads(p.stdout)==json.loads(Path("data/expected.json").read_text())

import pytest, math
from fabops.sensors import evaluate
S={'P':{'kind':'pressure','high':2000.0},'T':{'kind':'temperature','high':25.0}}
def val(x,u='Pa',s='P'):return evaluate({'sensor_id':s,'value':x,'unit':u},S)

def test_kpa_conversion(): assert val(3,'kPa')['status']=='ALARM'
def test_base_unit_normal(): assert val(1500)['status']=='OK'
def test_equal_not_alarm(): assert val(2000)['status']=='OK'
def test_missing(): assert val(None)['status']=='MISSING'
