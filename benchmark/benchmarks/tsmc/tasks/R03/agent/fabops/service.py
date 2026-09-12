import tempfile
from pathlib import Path
from .checkpoint import initialize,process,inspect,InjectedCrash

def run(data):
    with tempfile.TemporaryDirectory() as d:
        p=str(Path(d)/'c.db');initialize(p);failures=0
        for call in data['runs']:
            try:process(p,call['events'],call.get('fail_at'),call.get('crash_point'))
            except InjectedCrash:failures+=1
        return {'failures':failures,**inspect(p)}
