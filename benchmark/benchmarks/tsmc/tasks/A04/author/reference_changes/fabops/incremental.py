"""Checkpointed aggregates over an ordered ingestion stream."""
import copy, math
from .timeutil import timestamp

def initial_state():
    return {'last_offset':-1,'watermark':None,'seen':[],'totals':{}}

def update(state,batch):
    out=copy.deepcopy(state)
    seen=set(out['seen'])
    for row in sorted(batch,key=lambda r:r['offset']):
        if type(row['offset']) is not int or row['offset']<0: raise ValueError('invalid offset')
        if row['offset']<=out['last_offset']:continue
        t=timestamp(row['event_time'])
        value=float(row['value'])
        if not math.isfinite(value):raise ValueError('non-finite value')
        if row['event_id'] not in seen:
            target=out['totals'].setdefault(row['machine_id'],{'count':0,'sum':0.0})
            target['count']+=1;target['sum']+=value;seen.add(row['event_id'])
        if out['watermark'] is None or t>timestamp(out['watermark']):out['watermark']=t.isoformat()
        out['last_offset']=row['offset']
    out['seen']=sorted(seen)
    return out

def run(data):
    state=data.get('state') or initial_state()
    for batch in data['batches']:state=update(state,batch)
    return state
