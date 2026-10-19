"""D06 explicit test-fixture interactions; no enrollment or private answers."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from codecompass.app.study_d06 import StudyCollector
from scripts.B.export_d05 import export
from scripts.B.audit_d05 import audit


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True);a=p.parse_args()
    if not a.run_id.replace('-','').replace('_','').isalnum():p.error('safe run ID required')
    db=ROOT/'tmp'/(a.run_id+'.sqlite3')
    if db.exists():p.error('Preserve prior run')
    c=StudyCollector(ROOT,db,actor='test_fixture');operations=[]
    for tid in ('task_001','task_002'):
        for method in ('Ours','B2'):
            s=c.create(tid,method);sid=s['session_id'];s=c.action(sid,'complete_reading')
            if s['phase']!='quiz':raise ValueError('Automatic quiz not started')
            s=c.action(sid,'answer',{'choice':0}) # Explicit simulated response, never a real learner.
            while s['route']:
                c.action(sid,'read');s=c.action(sid,'complete_reading')
            s=c.action(sid,'submit',{'response':'D06 test fixture, not a real task solution'})
            operations.append(dict(task_id=tid,method=method,quiz_done=s['quiz_done'],status=s['status'],
                spent=s['spent'],success=s['success'],profile_is_simulated=True))
    out=ROOT/'experiments/B'/a.run_id/'fixtures/export01';counts=export(db,out,'test_fixture');result=audit(out)
    summary=dict(run_id=a.run_id,operations=operations,counts=counts,log_audit=result,formal_outcomes=0,model_api_calls=0)
    (out.parent/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(**counts,checks=result['checks'],passed=result['passed'],formal_outcomes=0)))
    raise SystemExit(0 if result['passed'] else 1)
