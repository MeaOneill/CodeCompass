"""Synthetic interaction inputs against real dev sources; never human records."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT))
from codecompass.app.experiment import Collector, METHODS
from scripts.B.export_d05 import export
from scripts.B.audit_d05 import audit


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True);a=p.parse_args()
    if not a.run_id.replace('-','').replace('_','').isalnum():p.error('safe run ID required')
    db=ROOT/'tmp'/(a.run_id+'.sqlite3')
    if db.exists():p.error('run already exists')
    c=Collector(ROOT,db,actor='test_fixture')
    for tid in ('task_001','task_002'):
        participant=None
        for method in METHODS:
            s=c.create(tid,method,participant);participant=s['participant'];sid=s['session_id']
            c.action(sid,'complete_reading');c.action(sid,'quiz')
            c.action(sid,'answer',{'choice':0}) # task_001 pass, task_002 fail; explicit fixtures.
            c.action(sid,'pause');c.action(sid,'resume')
            c.action(sid,'submit',{'response':'Synthetic development interaction; no actual task solution.'})
    out=ROOT/'experiments/B'/a.run_id/'fixtures/export01'
    counts=export(db,out,'test_fixture');result=audit(out)
    (out.parent/'audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(**counts,audit_passed=result['passed'],actual_human_sessions=0,model_api_calls=0)))
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
