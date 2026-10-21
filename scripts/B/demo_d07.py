"""Fixed two-repository development demo with explicitly synthetic answers."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from codecompass.app.journey_d07 import JourneyCollector,PRETEST,CROSS_ID,source_manifest
from scripts.B.audit_journey_d07 import audit
from scripts.B.export_d05 import export
from scripts.B.audit_d05 import audit as event_audit


def demo(run_id):
    if not run_id.replace('-','').replace('_','').isalnum():raise ValueError('Safe run id required')
    out=ROOT/'experiments/B'/run_id;out.mkdir(parents=True,exist_ok=False);database=ROOT/'tmp'/(run_id+'.sqlite3')
    if database.exists():raise FileExistsError('Preserve database')
    c=JourneyCollector(ROOT,database,actor='test_fixture');operations=[]
    for method in ('Ours','B2'):
        user=c.enroll(True)['participant'];c.pretest(user,[q['answer'] for q in PRETEST])
        for tid in ('task_002',CROSS_ID):
            if tid==CROSS_ID:c.transfer(user)
            s=c.create(tid,method,user);sid=s['session_id'];c.action(sid,'complete_reading');s=c.action(sid,'answer',{'choice':1})
            while s['route']:s=c.action(sid,'complete_reading')
            c.action(sid,'pause');c.action(sid,'resume')
            s=c.action(sid,'submit',{'response':json.dumps(dict(files={},outputs={},references=[],explanation='Explicit synthetic development fixture; not a final answer or human pilot'))})
            issue=c.issues(sid)
            operations.append(dict(task_id=tid,method=method,status=s['status'],success=s['success'],spent=s['spent'],
                source_version=s['task']['repo_commit'],route_explanations=bool(s['route_explanations']),issue_mode=issue['source_mode']))
        p=c.profile(user);assert p['evidence_count']==6 and p['transfers'][0]['target_retest_recorded']
    receipt=audit(database,'test_fixture');export(database,out/'fixtures/export','test_fixture');logs=event_audit(out/'fixtures/export')
    sources=source_manifest(ROOT)
    for rel in sources:
        p=out/'code_snapshot'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/rel).read_bytes())
    result=dict(run_id=run_id,actor='test_fixture',source_files=sources,operations=operations,receipt_audit=receipt,event_audit=logs,
        passed=receipt['passed'] and logs['passed'],formal_participants=0,model_calls=0,human_pilot_people_verified=False,actual_second_machine=False)
    (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(passed=result['passed'],sessions=len(operations),receipt_checks=receipt['checks'],event_checks=logs['checks'],model_calls=0)))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True);a=p.parse_args();raise SystemExit(0 if demo(a.run_id)['passed'] else 1)
