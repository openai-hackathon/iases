import json, subprocess, sys
from pathlib import Path

def test_hidden_cli_fixture():
    root=Path(__file__).parent.parent / "data"
    p=subprocess.run([sys.executable,"-m","fabops","--input",str(root/"request.json")],capture_output=True,text=True,timeout=10,check=True)
    assert json.loads(p.stdout)==json.loads((root/"expected.json").read_text())

import pytest, math
from fabops.sensors import evaluate
S={'P':{'kind':'pressure','high':2000.0},'T':{'kind':'temperature','high':25.0}}
def val(x,u='Pa',s='P'):return evaluate({'sensor_id':s,'value':x,'unit':u},S)

@pytest.mark.parametrize('value,unit',[(3000,'Pa'),(3,'kPa'),(.003,'MPa'),(30,'mbar')])
def test_equivalent_pressure(value,unit):
    r=val(value,unit);assert r['status']=='ALARM';assert r['value_base']==pytest.approx(3000)
@pytest.mark.parametrize('value,unit',[(25,'C'),(298.15,'K'),(77,'F')])
def test_equal_temperature(value,unit):
    r=val(value,unit,'T');assert r['status']=='OK';assert r['value_base']==pytest.approx(25)
def test_invalid_dimension(): assert val(20,'C')['status']=='INVALID'
def test_unknown_unit(): assert val(1,'psi')['status']=='INVALID'
def test_nan_inf():
    for x in [float('nan'),float('inf'),-float('inf')]:assert val(x)['status']=='INVALID'
def test_string_numeric(): assert val('3','kPa')['value_base']==3000
def test_invalid_string(): assert val('three')['status']=='INVALID'
def test_boolean_not_number(): assert val(True)['status']=='INVALID'
def test_unknown_sensor():
    with pytest.raises(ValueError):val(1,s='unknown')
def test_input_unchanged():
    r={'sensor_id':'P','value':3,'unit':'kPa'};evaluate(r,S);assert r['value']==3
