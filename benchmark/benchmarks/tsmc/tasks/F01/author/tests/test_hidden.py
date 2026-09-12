import json, subprocess, sys
from pathlib import Path

def test_hidden_cli_fixture():
    root=Path(__file__).parent.parent / "data"
    p=subprocess.run([sys.executable,"-m","fabops","--input",str(root/"request.json")],capture_output=True,text=True,timeout=10,check=True)
    assert json.loads(p.stdout)==json.loads((root/"expected.json").read_text())

import copy, itertools
from fabops.eligibility import eligible

def fixture(hold=False,status="WAITING",state="AVAILABLE",valid=True):
    return {"l":{"quality_hold":hold,"status":status,"product_id":"p","step_id":"s"}}, {"m":{"state":state}}, [{"machine_id":"m","product_id":"p","step_id":"s","valid":valid}]
def test_truth_table():
    for hold,status,state,valid in itertools.product([True,False],["WAITING","PROCESSING"],["AVAILABLE","LOCKED"],[True,False]):
        assert eligible("l","m",*fixture(hold,status,state,valid)) == (not hold and status=="WAITING" and state=="AVAILABLE" and valid)
def test_unknown_machine(): assert not eligible("l","z",*fixture())
def test_wrong_product():
    l,m,q=fixture();q[0]["product_id"]="different";assert not eligible("l","m",l,m,q)
def test_wrong_step():
    l,m,q=fixture();q[0]["step_id"]="next";assert not eligible("l","m",l,m,q)
def test_qualification_machine_isolation():
    l,m,q=fixture();q[0]["machine_id"]="other";assert not eligible("l","m",l,m,q)
def test_no_qualification():
    l,m,q=fixture();assert not eligible("l","m",l,m,[])
def test_revoked_only(): assert not eligible("l","m",*fixture(valid=False))
def test_duplicate_row_no_effect():
    l,m,q=fixture();assert eligible("l","m",l,m,q+q)
def test_hold_not_overridden_by_qualification(): assert not eligible("l","m",*fixture(hold=True))
def test_missing_records_fail_closed(): assert not eligible("l","m",{},{},[])
def test_input_not_mutated():
    args=fixture();before=copy.deepcopy(args);eligible("l","m",*args);assert args==before
def test_distinct_ids_no_hardcoding():
    l,m,q=fixture(True);l['lot-900']=l.pop('l');m['etch-77']=m.pop('m');q[0]['machine_id']='etch-77'
    assert not eligible('lot-900','etch-77',l,m,q)
