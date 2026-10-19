"""Complete E3 mean-gate control and direct current-candidate/B2 initial comparison."""
import argparse
import copy
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts.A.cases_d05 import development_cases
from scripts.A.cases_d04 import mechanism_cases
from codecompass.planner.adaptive import remaining_plan, route_audit
from codecompass.planner.core import greedy_plan
from codecompass.planner.g2_gate_control import mean_plan


def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes((json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8'))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-id',required=True);args=parser.parse_args()
    if not args.run_id.replace('-','').isalnum():parser.error('Unsafe run ID')
    out=ROOT/'experiments/A'/args.run_id;out.mkdir(exist_ok=False)
    candidate=json.loads((ROOT/'configs/frozen/v0.1-candidate/candidate.json').read_text(encoding='utf-8'))
    cases=development_cases()
    for c in cases:
        c['request']['budget']=candidate['budget'];c['group']='D06_candidate_inputs'
    for c in mechanism_cases():
        c['case_id']='D04-'+c['case_id'];c['group']='historical_structural_stress'
        cases.append(c)
    rows=[]
    started=dt.datetime.now().astimezone().isoformat()
    for case in cases:
        save(out/'inputs'/(case['case_id']+'.json'),case)
        req,units,state,config=[case[k] for k in ('request','units','state','config')]
        for method in ['candidate_lower','candidate_mean','B2_original']:
            if method=='candidate_mean':
                result=mean_plan(ROOT,req,units,state,config,options=candidate['search'])
            elif method=='candidate_lower':
                result=remaining_plan(ROOT,req,units,state,config,alpha=0,gamma=0,options=candidate['search'])
            else:
                plan,trace=greedy_plan(req,units,state,config)
                costs={u['id']:u['base_cost'] for u in units}
                replay=route_audit(req,units,trace['gate'],plan['ordered_units'],costs)
                assert replay['valid']
                result=dict(status=plan['status'],remaining=plan['ordered_units'],objective=plan['estimated_cost'],
                            gate=trace['gate'],replay=replay,original_plan=plan,original_trace=trace)
            assert result['status']!='FEASIBLE' or result['replay']['goal_complete']
            save(out/'runs'/case['case_id']/(method+'.json'),result)
            rows.append(dict(case_id=case['case_id'],group=case['group'],method=method,budget=req['budget'],
                status=result['status'],proxy_cost=result['objective'],
                gated_concepts='|'.join(sorted(c for c,g in result['gate'].items() if g['mastered'])),
                coverage_complete=result['replay']['goal_complete'],human_task_success=None))
    with (out/'comparison.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    save(out/'summary.json',dict(run_id=args.run_id,cases=len(cases),runs=len(rows),rows=rows,
        scope='initial planning only; no dynamic B2 or human feedback outcomes compared',
        formal_study_ready=False,new_model_calls=0,test_answers_used=False,all_candidates_retained=True))
    files=[ROOT/'src/codecompass/planner/g2_gate_control.py',ROOT/'scripts/A/run_d06_gate_control.py',
           ROOT/'tests/A/test_g2_gate_control.py',*sorted((ROOT/'src/codecompass/planner').glob('*.py')),
           ROOT/'src/codecompass/learner/model.py',ROOT/'scripts/A/cases_d04.py',ROOT/'scripts/A/cases_d05.py',
           ROOT/'configs/frozen/v0.1-candidate/candidate.json']
    files=sorted(set(files))
    for p in files:
        dest=out/'code_snapshot'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
    save(out/'registration.json',dict(owner='成员A',executor='Codex Agent A',machine=platform.node(),
        started_at=started,finished_at=dt.datetime.now().astimezone().isoformat(),
        source_base=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        command=[sys.executable,*sys.argv],exit_code=0,version='v0.1-candidate.1-supplement',
        affected_run_ids=[args.run_id],unchanged_prior_run_ids=['A-D06-controls03'],
        file_hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}))
    print(json.dumps(dict(runs=len(rows),cases=len(cases),exit_code=0)))


if __name__=='__main__':main()
