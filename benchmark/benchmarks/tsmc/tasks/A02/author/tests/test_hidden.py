import json, subprocess, sys
from pathlib import Path

def test_hidden_cli_fixture():
    root=Path(__file__).parent.parent / "data"
    p=subprocess.run([sys.executable,"-m","fabops","--input",str(root/"request.json")],capture_output=True,text=True,timeout=10,check=True)
    assert json.loads(p.stdout)==json.loads((root/"expected.json").read_text())

import pytest
from fabops.wafer_tests import summarize

def row(id='a',w='w',t='2026-01-15T00:00:00Z',res='PASS',lot='L',valid=True):
    return dict(test_id=id,wafer_id=w,tested_at=t,result=res,lot_id=lot,valid=valid)
def one(rows): return summarize(rows,['L'])[0]

def test_latest_fail_replaces_pass(): assert one([row(),row('b',t='2026-01-15T00:01:00Z',res='FAIL')])['passed']==0
def test_lexical_tie_break(): assert one([row('a'),row('z',res='FAIL')])['passed']==0
def test_utc_instant_tie(): assert one([row('a'),row('z',t='2026-01-15T08:00:00+08:00',res='FAIL')])['wafer_count']==1
def test_later_invalid_not_selected():
    r=one([row(),row('z',t='2027-01-01T00:00:00Z',res='FAIL',valid=False)]);assert r['passed']==1
def test_wafer_id_scoped_to_lot():
    r=summarize([row(),row('b',lot='X',res='FAIL')],['L','X']);assert [v['passed'] for v in r]==[1,0]
def test_exact_duplicate_invariant():
    r=row();assert one([r,r])==one([r])
def test_unsorted():
    x=[row('z',t='2026-01-16T00:00:00Z',res='FAIL'),row()];assert one(x)==one(x[::-1])
def test_empty_requested_lot(): assert summarize([],['other'])[0]['wafer_count']==0
def test_lot_order_deduplicated(): assert [x['lot_id'] for x in summarize([],['B','A','B'])]==['B','A']
def test_bad_valid_outcome():
    with pytest.raises(ValueError):one([row(res='UNKNOWN')])
def test_timestamp_requires_offset():
    with pytest.raises(ValueError):one([row(t='2026-01-01T00:00:00')])
def test_input_not_mutated():
    import copy
    x=[row(),row('b',res='FAIL')];b=copy.deepcopy(x);one(x);assert x==b
def test_independent_oracle_generated():
    import random
    rng=random.Random(1234);rows=[];expected_pass=0
    for w in range(35):
        outcomes=[rng.choice(['PASS','FAIL']) for _ in range(4)]
        expected_pass+=outcomes[-1]=='PASS'
        for n,outcome in enumerate(outcomes):rows.append(row(f'{w}-{n}',w=str(w),t=f'2026-01-15T00:0{n}:00Z',res=outcome))
    rng.shuffle(rows);r=one(rows);assert r['wafer_count']==35 and r['passed']==expected_pass
