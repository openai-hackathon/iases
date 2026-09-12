import json, subprocess, sys
from pathlib import Path

def test_public_cli_fixture():
    p=subprocess.run([sys.executable,"-m","fabops","--input","data/request.json"],capture_output=True,text=True,timeout=10,check=True)
    assert json.loads(p.stdout)==json.loads(Path("data/expected.json").read_text())

from fabops.eligibility import eligible

def env(hold=False,status="WAITING",state="AVAILABLE",valid=True):
    return {"x":{"quality_hold":hold,"status":status,"product_id":"P","step_id":"S"}}, {"m":{"state":state}}, [{"machine_id":"m","product_id":"P","step_id":"S","valid":valid}]
def test_hold_blocks_assignment(): assert not eligible("x","m",*env(hold=True))
def test_legal_assignment(): assert eligible("x","m",*env())
def test_machine_offline(): assert not eligible("x","m",*env(state="MAINTENANCE"))
def test_unknown_lot(): assert not eligible("absent","m",*env())
