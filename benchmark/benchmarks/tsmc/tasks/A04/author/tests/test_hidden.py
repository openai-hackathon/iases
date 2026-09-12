import json, subprocess, sys
from pathlib import Path

def test_hidden_cli_fixture():
    root=Path(__file__).parent.parent / "data"
    p=subprocess.run([sys.executable,"-m","fabops","--input",str(root/"request.json")],capture_output=True,text=True,timeout=10,check=True)
    assert json.loads(p.stdout)==json.loads((root/"expected.json").read_text())

import copy,json,pytest
from fabops.incremental import update,initial_state

def r(n,id=None,t='2026-01-15T00:01:00Z',m='M',v=1):
    return dict(offset=n,event_id=id or f'e{n}',event_time=t,machine_id=m,value=v)
def run(*batches):
    s=initial_state()
    for b in batches:s=update(s,b)
    return s

def test_late_event_with_new_offset(): assert run([r(0)],[r(1,t='2020-01-01T00:00:00Z')])['totals']['M']['count']==2
def test_resume_json_roundtrip():
    s=json.loads(json.dumps(run([r(0)])));assert update(s,[r(1)])['totals']['M']['count']==2
def test_duplicate_new_offset_advances_checkpoint():
    s=run([r(0),r(1,id='e0')]);assert s['totals']['M']['count']==1 and s['last_offset']==1
def test_replayed_old_offsets_not_counted():
    a=[r(0),r(1,t='2026-01-15T00:02:00Z')];assert run(a,a)==run(a)
def test_unsorted_batch_sorted_by_ingest_offset(): assert run([r(2),r(0),r(1)])['totals']['M']['count']==3
def test_machine_groups():
    s=run([r(0),r(1,m='N')]);assert set(s['totals'])=={'M','N'}
def test_watermark_not_cursor():
    s=run([r(0)],[r(1,t='2020-01-01T00:00:00Z')]);assert s['watermark']=='2026-01-15T00:01:00+00:00'
def test_partition_equivalence():
    rows=[r(i,t=f'2026-01-15T00:0{i%4}:00Z',v=i) for i in range(24)]
    assert run(rows)==run(rows[:7],rows[7:19],rows[19:])
def test_generated_expected_sum():
    import random
    rng=random.Random(99);rows=[r(i,t=f'2026-01-15T00:0{rng.randrange(5)}:00Z',v=i) for i in range(50)]
    s=run(*[[x] for x in rows]);assert s['totals']['M']=={'count':50,'sum':1225.0}
def test_no_input_mutation():
    s=initial_state();old=copy.deepcopy(s);update(s,[r(0)]);assert s==old
def test_invalid_offset():
    with pytest.raises(ValueError):run([r(-1)])
def test_invalid_value_atomic():
    s=initial_state();old=copy.deepcopy(s)
    with pytest.raises(ValueError):update(s,[r(0,v=float('inf'))])
    assert s==old
