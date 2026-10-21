import copy,json,hashlib
from pathlib import Path
from scripts.A.cases_d07 import development_case
from codecompass.app.relay_v2 import registry
from codecompass.planner.runtime_d07 import safe_remaining
from codecompass.planner.adaptive import request_for_state
from codecompass.planner.diagnostics import evidence_for
from codecompass.learner import update_evidence,beta_quantile
root=Path.cwd(); rows=[]
for record in registry(root)['records']:
    d=development_case(root,record['task_id'])
    def plan(data, completed=(),reference=(),spent=0):
        return safe_remaining(root,request_for_state(data['request'],data['state'],data['config']),data['units'],data['state'],data['config'],completed=completed,reference=reference,spent=spent)
    initial=plan(d); completed=initial['remaining'][:1]; suffix=initial['remaining'][1:]
    spent=sum(u['base_cost'] for u in d['units'] if u['id'] in completed)+1
    counterfactual=plan(d,completed,suffix,spent)
    counts={c:sum(c in u['concept_ids'] for u in d['units']) for c in d['target_concept_ids']}
    forced=all(any(c in counts and counts[c]==1 for c in u['concept_ids']) for u in d['units'])
    for outcome in ['pass','fail']:
        nd=copy.deepcopy(d); ev=evidence_for(nd['request'],nd['state'],nd['quiz'],outcome,'2026-10-21T21:00:00+08:00')
        nd['state'],accepted=update_evidence(nd['state'],ev,allow_simulated=True)
        after=plan(nd,completed,suffix,spent)
        rows.append(dict(task_id=record['task_id'],outcome=outcome,units=len(d['units']),all_units_forced=forced,
            initial_status=initial['status'],status=after['status'],accepted=accepted,completed=completed,
            suffix_before_feedback=suffix,suffix_after_feedback=after['remaining'],
            counterfactual_same_spent=counterfactual['remaining'],
            feedback_changed_route=after['remaining']!=counterfactual['remaining'],
            suffix_changed=after['remaining']!=suffix,
            mastered_after=[c for c,g in after['gate'].items() if g['mastered']],
            completed_preserved=after['completed']==completed and not set(completed)&set(after['remaining'])))
assert len(rows)==24
assert all(r['status']=='FEASIBLE' and r['accepted']=='ACCEPTED' and r['all_units_forced'] and not r['feedback_changed_route'] and not r['suffix_changed'] and not r['mastered_after'] and r['completed_preserved'] for r in rows)
result=dict(head='588920db9c9b5c041d9687724203da941aef7296',fixture_only=True,scenarios=len(rows),feedback_changes=0,
    beta_single_pass=beta_quantile(2,1,.1),beta_single_fail=beta_quantile(1,2,.1),
    min_all_passes_to_master=next(n for n in range(1,20) if beta_quantile(n+1,1,.1)>=.7),rows=rows)
(root/'tmp/independent-audit/feedback_counterexamples.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
