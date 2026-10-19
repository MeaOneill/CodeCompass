"""Evaluator-only positive/negative fixtures, never planner test results.

Expected outputs stay in ignored jobs/SQLite. Neither application nor model
receives the reference fixture. This checks grading wiring, not task difficulty.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from codecompass.app.relay_v2 import RelayCollector
from scripts.B.grade_session_v2 import assess
from scripts.B.export_relay_v2 import export_assessed
from scripts.B.audit_d05 import audit


def verify(run_id,private_key):
    if not run_id.replace('-','').replace('_','').isalnum():raise ValueError('Safe run id required')
    out=ROOT/'experiments/B'/run_id;out.mkdir(parents=True,exist_ok=False)
    database=ROOT/'tmp'/(run_id+'.sqlite3')
    if database.exists():raise FileExistsError('Fresh fixture DB required')
    c=RelayCollector(ROOT,database,actor='test_fixture');rows=[]
    catalog=json.loads((ROOT/'benchmarks/B/task_catalog.json').read_text(encoding='utf-8'))['tasks']
    for task in catalog:
        tid=task['task_id']
        if tid in ('task_001','task_002'):continue
        key=ROOT/'benchmarks/B/dev_response_keys.json' if task['split']=='dev' else Path(private_key)
        for variant in ('positive_reference','negative_empty'):
            s=c.create(tid,'B2');sid=s['session_id'];c.action(sid,'complete_reading');c.action(sid,'answer',{'choice':0})
            # Build only after planning. No gold enters source/route generation.
            expected=json.loads(key.read_text(encoding='utf-8'))['tasks'][tid]['outputs']
            response=dict(outputs=expected if variant=='positive_reference' else {},
                references=[{k:span[k] for k in ('path','start_line','end_line')} for span in task['source_spans']],
                explanation='Explicit scorer fixture; no real task solution, learner or human review')
            c.action(sid,'submit',{'response':json.dumps(response,ensure_ascii=False)})
            r=assess(database,sid,ROOT/'tmp'/run_id/tid/variant,key=key)
            ok=(r['status']=='PENDING' and r['success'] is None and r['automated_score']==8) if variant=='positive_reference' else (r['success'] is False and r['automated_score']==2)
            rows.append(dict(task_id=tid,fixture=variant,assessment_expected=ok,status=r['status'],review_count=r['review_count'],
                visible_result_bound=c.get(sid)['assessment']['input_response_sha256']==r['input_response_sha256']))
    counts=export_assessed(database,out/'fixtures/export','test_fixture')
    log_audit=audit(out/'fixtures/export')
    result=dict(run_id=run_id,scope='evaluator-only synthetic positive/negative fixtures; not formal method outcomes',
        cases=rows,passed=all(r['assessment_expected'] and r['visible_result_bound'] for r in rows),
        private_key_sha256=hashlib.sha256(Path(private_key).read_bytes()).hexdigest(),answers_exported=False,human_reviews=0,model_api_calls=0,
        export_counts=counts,event_audit=log_audit)
    (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(passed=result['passed'],cases=len(rows),answers_exported=False,human_reviews=0)))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True);p.add_argument('--private-key',type=Path,required=True);a=p.parse_args()
    raise SystemExit(0 if verify(a.run_id,a.private_key)['passed'] else 1)
