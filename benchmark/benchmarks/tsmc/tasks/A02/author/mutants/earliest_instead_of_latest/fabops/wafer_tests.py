"""Latest valid wafer-test outcome summaries."""
from .timeutil import timestamp

def summarize(rows, lot_ids):
    requested=list(dict.fromkeys(lot_ids))
    valid=[]
    for r in rows:
        if r['lot_id'] not in requested or not r['valid']: continue
        if r['result'] not in {'PASS','FAIL'}: raise ValueError('invalid test result')
        timestamp(r['tested_at'])
        valid.append(r)
    latest={}
    for r in valid:
        key=(r['lot_id'],r['wafer_id'])
        rank=(timestamp(r['tested_at']),r['test_id'])
        if key not in latest or rank<latest[key][0]: latest[key]=(rank,r)
    selected=[record for _,record in latest.values()]
    result=[]
    for lot in requested:
        items=[r for r in selected if r['lot_id']==lot]
        passed=sum(r['result']=='PASS' for r in items)
        result.append({'lot_id':lot,'wafer_count':len(items),'passed':passed,
                       'pass_ratio':passed/len(items) if items else None})
    return result

def run(data): return summarize(data['rows'],data['lot_ids'])
