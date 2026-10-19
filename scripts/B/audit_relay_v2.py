"""Read-only candidate2 audit; cached API responses only, no paid calls."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from codecompass.app.relay_v2 import registry,prepare
from codecompass.app.experiment import digest
from scripts.B.comparison.b1 import digest as request_digest
from scripts.B.audit_d05 import audit as event_audit


def audit(root=ROOT):
    root=Path(root);errors=[];checks=0
    def check(condition,label):
        nonlocal checks
        checks+=1
        if not condition:errors.append(label)
    seal=json.loads((root/'benchmarks/B/frozen/B-D06-v0.2-candidate/manifest.json').read_text(encoding='utf-8'))
    for row in seal['files']:
        p=(root/row['path']).resolve()
        check(p.is_relative_to(root.resolve()) and p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],'sealed file '+row['path'])
    check(seal['formal_freeze'] is False,'candidate must not pretend formal freeze')
    rows=registry(root)['records'];check(len(rows)==12,'12 actual tasks')
    check(sum(r['split']=='dev' for r in rows)==4 and sum(r['split']=='test_candidate' for r in rows)==8,'4/8 split')
    for r in rows:
        d=prepare(root,r['task_id'],'p_'+'0'*32,True)
        check(bool(d['materials']) and sum(u['base_cost'] for u in d['units'])+1<=100,'source/cost '+r['task_id'])
        check(d['human_review']=='NOT_REVIEWED' and 'answer' not in d['public_quiz'],'no fabricated human/key '+r['task_id'])
    for run in ('B-D06-v2-offline01','B-D06-v2-live01'):
        folder=root/'experiments/B'/run;s=json.loads((folder/'summary.json').read_text(encoding='utf-8'))
        check(s['passed'] and s['formal_outcomes']==0 and s['fixture_inputs'] is True,'run provenance '+run)
        a=event_audit(folder/'fixtures/export');check(a['passed'],'event replay '+run)
    live=root/'experiments/B/B-D06-v2-live01';traces=json.loads((live/'traces.json').read_text(encoding='utf-8'))
    check(len({digest(r['traces'][0]['context']) for r in traces})==1,'same initial information')
    calls=[]
    for r in traces:
        check(len(r['traces'])==2,'initial and feedback '+r['method'])
        for t in r['traces']:
            ctx=t['context'];check(t['status']=='FEASIBLE' and not set(t['route'])&set(ctx['completed']),'valid completed-prefix '+r['method'])
            for call in t['details'].get('calls',[]):
                calls.append(call)
                check(t['details']['transport_is_fixture'] is False,'actual model transport')
                check(request_digest(call['request'])==call['request_hash'],'request bytes')
                check(json.loads(call['request']['input'].split('CONTEXT_JSON\n')[1])==ctx,'request matches public context')
                check(call['model_returned']==call['model_requested'] and call['usage'] is not None,'model and usage')
                check(call['quarantined'] is False and call['estimated_cost_cny'] is not None,'safe raw response and accounted cost')
    check(len(calls)==2,'actual initial and replan calls')
    s=json.loads((live/'summary.json').read_text(encoding='utf-8'))
    check(s['model_reservation_before_cny']==1.5 and s['model_reservation_after_cny']==2 and s['cumulative_budget_cny']==5,'same cumulative budget')
    scoring=json.loads((root/'experiments/B/B-D06-v2-scorer02/summary.json').read_text(encoding='utf-8'))
    check(scoring['passed'] and len(scoring['cases'])==20 and not scoring['answers_exported'] and scoring['human_reviews']==0,'independent scoring fixtures')
    check(event_audit(root/'experiments/B/B-D06-v2-scorer02/fixtures/export')['passed'],'scored event export replay')
    return dict(candidate_checks_passed=not errors,checks=checks,errors=errors,task_specs=12,executable_tasks=12,
        actual_model_api_calls=len(calls),actual_enrollment=None,formal_tasks=0,human_review='NOT_REVIEWED',
        software_handoff_ready=not errors,joint_g2_passed=False,formal_study_allowed=False,freeze_tag_allowed=False,
        remaining=['actual recruitment/consent','actual task/source/protocol review and A/B comparison-branch confirmation','designated integration and formal version/tag'],
        historical_audit_policy='v0.1 reports describe immutable previous checkpoint; this v0.2 audit supersedes its technical missing items')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();result=audit()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=False));raise SystemExit(0 if result['candidate_checks_passed'] else 1)
