"""Trace lots whose processing intervals overlap an equipment incident."""
from .timeutil import timestamp

def interval(row,start,end):
    a,b=timestamp(row[start]),timestamp(row[end])
    if b<a:raise ValueError('reversed interval')
    return a,b

def impacted_lots(steps,events):
    parsed_steps=[(s,*interval(s,'enter','exit')) for s in steps]
    parsed_events=[(e,*interval(e,'start','end')) for e in events]
    matches={}
    for s,a,b in parsed_steps:
        for e,c,d in parsed_events:
            if s['machine_id']==e['machine_id'] and max(a,c)<=min(b,d):
                matches.setdefault(s['lot_id'],set()).add(e['event_id'])
    return [{'lot_id':lot,'event_ids':sorted(matches[lot])} for lot in sorted(matches)]

def run(data): return impacted_lots(data['steps'],data['events'])
