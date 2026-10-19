"""Labelled fixture playback on real sources. --live uses the shared CNY5 ledger."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from codecompass.app.relay_v2 import RelayCollector
from scripts.B.comparison.b1 import PersistentSpendMeter
from scripts.B.export_d05 import export
from scripts.B.audit_d05 import audit


class RunCap:
    def __init__(self,meter):self.meter=meter;self.calls=0
    def reserve(self,amount):
        if self.calls>=4:return False
        accepted=self.meter.reserve(amount)
        if accepted:self.calls+=1
        return accepted


def run(run_id,live=False):
    if not run_id.replace('-','').replace('_','').isalnum():raise ValueError('Safe run id required')
    out=ROOT/'experiments/B'/run_id;out.mkdir(parents=True,exist_ok=False)
    db=ROOT/'tmp'/(run_id+'.sqlite3')
    if db.exists():raise FileExistsError('Preserve prior database')
    cfg=json.loads((ROOT/'configs/B/D06_v2_deepseek.json').read_text(encoding='utf-8'))['b1'] if live else None
    meter=PersistentSpendMeter(ROOT/cfg['budget_state_path'],5,'CNY') if live else None
    before=meter.reserved if meter else None
    capped=RunCap(meter) if meter else None
    c=RelayCollector(ROOT,db,actor='test_fixture',b1_config=cfg,meter=capped)
    operations=[];traces=[]
    tids=['task_001'] if live else [f'task_{i:03}' for i in range(1,13)]
    methods=('Ours','B2','B1') if live else ('Ours','B2')
    for tid in tids:
        for method in methods:
            s=c.create(tid,method);sid=s['session_id']
            if s['status']=='ACTIVE':
                s=c.action(sid,'complete_reading');s=c.action(sid,'answer',{'choice':0})
                while s['route'] and s['status']=='ACTIVE':s=c.action(sid,'complete_reading')
                if s['status']=='ACTIVE':s=c.action(sid,'submit',{'response':json.dumps(dict(outputs={},references=[],explanation='Engineering fixture; not a real answer or participant'))})
            ts=c.traces(sid)
            traces.append(dict(task_id=tid,method=method,traces=ts))
            operations.append(dict(task_id=tid,method=method,status=s['status'],spent=s['spent'],quiz_done=s['quiz_done'],
                success=s['success'],profile_is_simulated=True,source_commit=s['task']['repo_commit']))
    counts=export(db,out/'fixtures/export','test_fixture');log=audit(out/'fixtures/export')
    calls=[call for t in traces for trace in t['traces'] for call in trace['details'].get('calls',[])]
    summary=dict(run_id=run_id,actor='test_fixture',operations=operations,counts=counts,event_audit=log,
        model_api_calls=len(calls),model_reservation_before_cny=before,model_reservation_after_cny=meter.reserved if meter else None,
        cumulative_budget_cny=5,estimated_cost_cny=sum(v['estimated_cost_cny'] or 0 for v in calls),actual_bill_cny=None,
        formal_outcomes=0,human_participants=0,fixture_inputs=True,real_model_transport=live,
        passed=log['passed'] and all(r['status']=='SUBMITTED' for r in operations))
    for name,value in [('traces.json',traces),('summary.json',summary)]:
        (out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:summary[k] for k in ('run_id','passed','model_api_calls','estimated_cost_cny','model_reservation_after_cny')},ensure_ascii=False))
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True);p.add_argument('--live',action='store_true');a=p.parse_args()
    raise SystemExit(0 if run(a.run_id,a.live)['passed'] else 1)
