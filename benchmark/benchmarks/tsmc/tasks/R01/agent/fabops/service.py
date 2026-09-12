import tempfile
from pathlib import Path
from .work_orders import initialize,submit,count_work_orders,ConflictError

def run(data):
    with tempfile.TemporaryDirectory() as d:
        path=str(Path(d)/'orders.db');initialize(path);responses=[]
        for req in data['requests']:
            try: responses.append({'ok':submit(path,req['key'],req['payload'],req.get('lose_response',False))})
            except (ConflictError,ConnectionError,ValueError) as exc: responses.append({'error':type(exc).__name__})
        return {'responses':responses,'work_orders':count_work_orders(path)}
