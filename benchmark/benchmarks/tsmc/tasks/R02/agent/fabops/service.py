import tempfile
from pathlib import Path
from .reservations import initialize,reserve,used_units,release

def run(data):
    with tempfile.TemporaryDirectory() as d:
        p=str(Path(d)/'r.db');initialize(p,data['capacities']);out=[]
        for req in data['requests']:
            if req.get('op')=='release':out.append(release(p,req['id']))
            else:out.append(reserve(p,req['id'],req['machine'],req.get('units',1)))
        return {'accepted':out,'used':{m:used_units(p,m) for m in data['capacities']}}
