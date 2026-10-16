"""Strict D03 artifact and challenge audit, independent of greedy selection."""
import argparse,copy,hashlib,json,sys,traceback,xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT))
from codecompass.learner import mastery_gate
from codecompass.planner import check_plan
from codecompass.graph import read_snapshot,validate_span
from codecompass.retrieval.samples import contract_validator
from scripts.B.b0 import fixed_order


def main():
 p=argparse.ArgumentParser();p.add_argument('--source-run',required=True);p.add_argument('--run-id',required=True);a=p.parse_args()
 if not all(v.replace('-','').replace('_','').isalnum() for v in vars(a).values()):p.error('Invalid run IDs')
 out=ROOT/'experiments/A'/a.run_id;out.mkdir(parents=True,exist_ok=False)
 source=ROOT/'experiments/A'/a.source_run
 load=lambda p:json.loads(p.read_text(encoding='utf-8'))
 checks=[]
 def check(label,condition):
  checks.append({'check':label,'passed':bool(condition)})
  if not condition:raise AssertionError(label)
 try:
  config=load(source/'config.json');summary=load(source/'summary.json')
  schema=Draft202012Validator(load(ROOT/'schemas/contracts-1.1.schema.json'),format_checker=contract_validator(ROOT).format_checker)
  snap=load(ROOT/'benchmarks/sources/boltons/snapshot.json');contents=read_snapshot(ROOT/'benchmarks/sources/boltons',snap)
  for row in load(source/'input_manifest.json'):
   check('current input hash '+row['path'],hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256'])
   check('frozen input hash '+row['path'],hashlib.sha256((ROOT/row['frozen_copy']).read_bytes()).hexdigest()==row['sha256'])
  check('two tasks by two profiles and two methods plus preserved failure pair',len(summary['cases'])==10)
  identities=set();negative_count=0
  for case in summary['cases']:
   key=(case['case_id'],case['method']);check('unique case method '+str(key),key not in identities);identities.add(key)
   folder=source/'cases'/case['case_id'];req=load(folder/'request.json');us=load(folder/'units.json');ledger=load(folder/'learner_ledger.json')
   task=load(ROOT/'benchmarks/dev/D03'/f'{case["task_id"]}.json');schema.validate(task);schema.validate(req);schema.validate(case['plan'])
   check('goals match independent B task specification '+str(key),set(req['target_concept_ids'])==set(task['required_concept_ids']))
   check('same actual candidate pool '+str(key),set(req['unit_ids'])==set(task['learning_unit_ids'])=={u['id'] for u in us})
   check('all profiles explicitly simulated '+str(key),case['is_simulated'] is True and req['is_fixture'] is True and ledger['is_simulated'] is True)
   check('no fabricated human/task success '+str(key),case['independent_task_success'] is None and case['human_elapsed_minutes'] is None)
   for u in us:
    schema.validate(u)
    for span in u['source_spans']:validate_span(span,snap,contents)
    check('same measured source cost '+u['id']+' '+str(key),u['base_cost']==config['unit_costs'][u['id']]==sum(s['end_line']-s['start_line']+1 for s in u['source_spans']))
    check('no unreviewed real hard edges '+u['id']+' '+str(key),not any(e['hard'] for e in u['prerequisites']))
   gate=mastery_gate(ledger,req['snapshot_id'],{c for u in us for c in u['concept_ids']}|set(req['target_concept_ids']),threshold=config['threshold'],quantile=config['quantile'],allow_simulated=True)
   detail=load(folder/'gate_and_choices.json');check('gate independently recomputed '+str(key),gate==detail['gate'])
   audit=check_plan(req,us,case['plan'],gate);check('route replay valid '+str(key),audit['structurally_valid'])
   check('saved and replay audit agree '+str(key),audit==case['audit'])
   if case['method']=='B0':
    raw=fixed_order(us,config['routes'][case['task_id']],req['budget'],'proxy_cost');check('B0 unchanged public implementation '+str(key),raw==load(folder/'B0_raw.json') and raw['ordered_units']==case['plan']['ordered_units'])
   # Fail closed on mutated numeric claims, coverage, duplication, and status.
   mutants=[]
   bad=copy.deepcopy(case['plan']);bad['estimated_cost']+=1;mutants.append(bad)
   bad=copy.deepcopy(case['plan']);bad['coverage']['ratio']=-1;mutants.append(bad)
   bad=copy.deepcopy(case['plan']);bad['status']='INFEASIBLE_PROVEN';bad['proof_path']='fake-proof';mutants.append(bad)
   if case['plan']['ordered_units']:
    bad=copy.deepcopy(case['plan']);bad['ordered_units'].append(bad['ordered_units'][0]);mutants.append(bad)
   if case['plan']['status']=='NO_FEASIBLE_FOUND':
    bad=copy.deepcopy(case['plan']);bad['status']='FEASIBLE';bad['unmet_constraints']=[];mutants.append(bad)
   for bad in mutants:
    check('mutated route rejected '+str(key)+' #'+str(negative_count),not check_plan(req,us,bad,gate)['structurally_valid']);negative_count+=1
  for tid in ['task_001','task_002']:
   baseline=next(c for c in summary['cases'] if c['task_id']==tid and c['profile_id']=='sim_unknown' and c['method']=='B2_initial' and 'failure' not in c['case_id'])
   known=next(c for c in summary['cases'] if c['task_id']==tid and c['profile_id']=='sim_evidence' and c['method']=='B2_initial')
   check('ability input leads to an explainable actual decision difference '+tid,baseline['plan']['ordered_units']!=known['plan']['ordered_units'])
  check('all five A-only boundary checks retained',len(summary['boundaries'])==5 and all(t['passed'] for t in summary['boundaries']))
  counter=load(source/'boundary_suite/greedy_counterexample.json')
  check('greedy failure alongside valid feasible witness is disclosed',counter['plan']['status']=='NO_FEASIBLE_FOUND' and counter['plan']['proof_path'] is None and counter['witness_audit']['structurally_valid'])
  shared=load(source/'boundary_suite/shared_prerequisite.json')
  check('shared prerequisite counted once',shared['plan']['ordered_units'].count('s')==1 and shared['plan']['estimated_cost']==5)
  check('diagnostics not claimed',config['diagnostics_implemented'] is False)
  check('no formal study claimed',config['formal_study_ready'] is False and summary['formal_study_ready'] is False)
  figures=ROOT/'report_materials/A/A-D03'/a.source_run
  render=load(figures/'render_config.json')
  check('figure source hash',render['source_sha256']==hashlib.sha256((source/'summary.json').read_bytes()).hexdigest())
  for name in ['task_001_paired_routes','task_002_paired_routes','failure_budget_route']:
   with Image.open(figures/(name+'.png')) as im:im.verify()
   with Image.open(figures/(name+'.png')) as im:check('PNG300dpi '+name,all(abs(d-300)<.1 for d in im.info['dpi']))
   svg=ET.parse(figures/(name+'.svg')).getroot();check('native SVG '+name,bool(svg.findall('{http://www.w3.org/2000/svg}text')) and not svg.findall('.//{http://www.w3.org/2000/svg}image'))
  payload={'task_id':'A-D03','source_run':a.source_run,'audit_run':a.run_id,'engineering_passed':True,'checks':checks,'negative_mutations_rejected':negative_count,
           'independent_human_review':'NOT_REVIEWED','formal_study_ready':False,'next_step_allowed_pending_sync':False,'remaining_engineering_items':['fresh committed-copy replay and remote SHA verification'],'exit_code':0}
 except Exception:
  payload={'engineering_passed':False,'checks':checks,'error':traceback.format_exc(),'next_step_allowed_pending_sync':False,'exit_code':1}
 (out/'audit.json').write_bytes((json.dumps(payload,ensure_ascii=False,indent=2)+'\n').encode())
 print(json.dumps({k:v for k,v in payload.items() if k!='checks'},ensure_ascii=False,indent=2));return payload['exit_code']

if __name__=='__main__':raise SystemExit(main())
