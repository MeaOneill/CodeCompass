"""Reproducible D03 development short tests; no human outcomes or hidden keys."""
import argparse,copy,csv,datetime,hashlib,importlib.util,json,os,platform,subprocess,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT))
from jsonschema import Draft202012Validator
from codecompass.retrieval.samples import contract_validator
from codecompass.graph import read_snapshot,validate_span
from codecompass.learner import initial_state,update_evidence,planning_rows,mastery_gate
from codecompass.planner import greedy_plan,check_plan,PlanningInputError,plan_request
from scripts.B.b0 import fixed_order


def load(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def save(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode())


def make_profile(description,snapshot):
 state=initial_state(description['id'],is_simulated=True)
 for concept in description['known_concepts']:
  for n in range(10):
   e={'schema_version':'1.0.0','object_type':'LearnerEvidence','is_fixture':True,'evidence_id':f'{description["id"]}:{concept}:e{n}',
      'pseudonymous_user_id':description['id'],'concept_id':concept,'item_id':f'synthetic:{concept}:item{n}','outcome':'pass',
      'timestamp':'2026-10-16T00:00:00+08:00','project':snapshot,'evidence_type':'independent_quiz','attempt_id':f'synthetic_attempt{n}','independent':True}
   state,decision=update_evidence(state,e,allow_simulated=True);assert decision=='ACCEPTED'
 return state


def make_request(task,units,state,config,request_id,budget=None):
 return {'schema_version':'1.0.0','object_type':'PlanningRequest','is_fixture':True,'request_id':request_id,'snapshot_id':task['snapshot_id'],'task_id':task['task_id'],
         'learner_state':planning_rows(state,task['snapshot_id'],quantile=config['quantile'],allow_simulated=True),'budget':config['budget'] if budget is None else budget,
         'cost_unit':'proxy_cost','config_version':config['version'],'target_concept_ids':task['required_concept_ids'],'unit_ids':[u['id'] for u in units],'prior_plan_id':None}


def b0_adapter(request,units,order,gate):
 raw=fixed_order(units,order,request['budget'],request['cost_unit'])
 if raw['status']=='INPUT_INCOMPLETE':raise PlanningInputError('B0 received missing common costs')
 chosen=raw['ordered_units'];by_id={u['id']:u for u in units};known={c for c,g in gate.items() if g['mastered']}
 for uid in chosen:known.update(by_id[uid]['concept_ids'])
 goals=set(request['target_concept_ids']);missing=sorted(goals-known)
 trace=[]
 for uid in chosen:
  u=by_id[uid];source='; '.join(f'{s["path"]}:L{s["start_line"]}-{s["end_line"]}' for s in u['source_spans'])
  trace.append({'step':len(trace)+1,'unit_id':uid,'reason':f'B0 FIXED_DOCUMENT_PREFIX; common proxy_cost={u["base_cost"]}; source={source}; selection intentionally ignores profile','evidence_ids':[]})
 p={'schema_version':'1.0.0','object_type':'PlanResult','is_fixture':True,'plan_id':request['request_id']+'-B0','request_id':request['request_id'],
    'status':'FEASIBLE' if not missing else 'NO_FEASIBLE_FOUND','ordered_units':chosen,
    'coverage':{'required_concept_ids':sorted(goals),'covered_concept_ids':sorted(goals&known),'ratio':len(goals&known)/len(goals) if goals else None},
    'unmet_constraints':['uncovered target: '+c for c in missing]+([] if not missing else ['B0 fixed prefix did not yield a complete route within the same budget']),
    'estimated_cost':raw['estimated_cost'],'cost_unit':'proxy_cost','reason_trace':trace,'proof_path':None}
 return p,raw


def structural_unit(uid,concepts,cost=1,deps=()):
 return {'schema_version':'1.0.0','object_type':'LearningUnit','is_fixture':True,'id':uid,'source_spans':[],'concept_ids':list(concepts),'base_cost':cost,'cost_unit':'proxy_cost',
         'prerequisites':[{'unit_id':d,'relation_type':'teaching_prerequisite','hard':True,'provenance':{'kind':'fixture','review_status':'approved','reviewer':'SYNTHETIC_REVIEW_NOT_A_PERSON','evidence':['fixture-only:structural-constraint']}} for d in deps]}


def execute(out,run_id):
 config=load('configs/A/D03_common.json');profiles=load('configs/A/D03_profiles.json')['profiles'];units=load('benchmarks/dev/D03/units.json');by_id={u['id']:u for u in units}
 validator=Draft202012Validator(load('schemas/contracts-1.1.schema.json'),format_checker=contract_validator(ROOT).format_checker)
 snap=load('benchmarks/sources/boltons/snapshot.json');contents=read_snapshot(ROOT/'benchmarks/sources/boltons',snap)
 for u in units:
  validator.validate(u)
  for span in u['source_spans']:validate_span(span,snap,contents)
 assert hashlib.sha256((ROOT/config['documentation']['path']).read_bytes()).hexdigest()==config['documentation']['sha256']
 results=[]
 def case(task,description,case_id,budget=None):
  us=[copy.deepcopy(by_id[uid]) for uid in task['learning_unit_ids']];state=make_profile(description,task['snapshot_id']);req=make_request(task,us,state,config,case_id,budget)
  validator.validate(req);plan,detail=plan_request(ROOT,req,us,state,config);b0,raw=b0_adapter(req,us,config['routes'][task['task_id']],detail['gate'])
  folder=out/'cases'/case_id;save(folder/'request.json',req);save(folder/'learner_ledger.json',state);save(folder/'units.json',us);save(folder/'gate_and_choices.json',detail);save(folder/'B0_raw.json',raw)
  for method,p in [('B0',b0),('B2_initial',plan)]:
   validator.validate(p);audit=check_plan(req,us,p,detail['gate']);assert audit['structurally_valid'],audit
   record={'case_id':case_id,'task_id':task['task_id'],'profile_id':description['id'],'profile_label':description['label'],'method':method,'is_simulated':True,
           'evidence_type':'development_short_test','budget':req['budget'],'cost_unit':'proxy_cost','plan':p,'audit':audit,'independent_task_success':None,
           'human_elapsed_minutes':None,'formal_study_result':False,'sources':{u['id']:u['source_spans'] for u in us}}
   save(folder/(method+'.json'),record);results.append(record)
  return plan
 for tid in ['task_001','task_002']:
  task=load('benchmarks/dev/D03/'+tid+'.json');validator.validate(task)
  for profile in profiles:
   p=case(task,profile,tid+'-'+profile['id']);assert p['status']=='FEASIBLE'
 failure=case(load('benchmarks/dev/D03/task_001.json'),profiles[0],'task_001-budget_failure',20)
 assert failure['status']=='NO_FEASIBLE_FOUND' and failure['proof_path'] is None
 # A-only boundary suite; NOT the joint G1 T3 capability/Issue check assigned to B.
 fixtures={
  'shared_prerequisite':([structural_unit('s',['base']),structural_unit('a',['x'],2,['s']),structural_unit('b',['y'],2,['s'])],['x','y'],5),
  'cycle':([structural_unit('a',['x'],1,['b']),structural_unit('b',['y'],1,['a'])],['x'],100),
  'unreachable':([structural_unit('a',['x'])],['missing'],100),
  'greedy_counterexample':([structural_unit('a',['x'],2),structural_unit('b',['x','y'],5),structural_unit('c',['y'],4)],['x','y'],5)}
 boundary=[]
 for name,(us,goals,budget) in fixtures.items():
  task={'task_id':'structural_'+name,'snapshot_id':snap['snapshot_id'],'required_concept_ids':goals};state=make_profile(profiles[0],snap['snapshot_id']);req=make_request(task,us,state,config,'boundary-'+name,budget)
  p,d=greedy_plan(req,us,state,config);audit=check_plan(req,us,p,d['gate']);assert audit['structurally_valid']
  expected='FEASIBLE' if name=='shared_prerequisite' else 'NO_FEASIBLE_FOUND';assert p['status']==expected
  record={'is_fixture':True,'scope':'A-only synthetic structural boundary test; not joint G1 T3','name':name,'request':req,'units':us,'plan':p,'detail':d,'audit':audit,'expected_status':expected}
  if name=='greedy_counterexample':
   witness=copy.deepcopy(p);witness.update(status='FEASIBLE',ordered_units=['b'],estimated_cost=5,unmet_constraints=[]);witness['coverage'].update(covered_concept_ids=['x','y'],ratio=1)
   witness_audit=check_plan(req,us,witness,d['gate']);assert witness_audit['structurally_valid'];record.update(known_feasible_witness=witness,witness_audit=witness_audit)
  save(out/'boundary_suite'/(name+'.json'),record);boundary.append({'name':name,'status':p['status'],'expected':expected,'passed':True})
 # Unknown costs must produce explicit input failure, never a zero-cost route.
 missing=copy.deepcopy(units[:1]);missing[0]['base_cost']=None;state=make_profile(profiles[0],snap['snapshot_id']);req=make_request({'task_id':'missing_cost','snapshot_id':snap['snapshot_id'],'required_concept_ids':missing[0]['concept_ids']},missing,state,config,'boundary-missing-cost')
 try:greedy_plan(req,missing,state,config)
 except PlanningInputError as e:
  save(out/'boundary_suite/missing_cost.json',{'expected_rejection':True,'error_type':type(e).__name__,'message':str(e),'no_success_plan_created':True});boundary.append({'name':'missing_cost','passed':True,'status':'INPUT_REJECTED'})
 else:raise AssertionError('Null cost was not rejected')
 save(out/'boundary_suite/summary.json',boundary)
 save(out/'summary.json',{'run_id':run_id,'cases':results,'boundaries':boundary,'is_simulated':True,'formal_study_ready':False,'independent_task_success':None})
 with (out/'routes.csv').open('w',encoding='utf-8',newline='') as f:
  fields=['case_id','task_id','profile','method','status','route','proxy_cost','covered','required','is_simulated','independent_task_success'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in results:
   p=r['plan'];w.writerow(dict(case_id=r['case_id'],task_id=r['task_id'],profile=r['profile_id'],method=r['method'],status=p['status'],route=' -> '.join(p['ordered_units']),proxy_cost=p['estimated_cost'],covered=len(p['coverage']['covered_concept_ids']),required=len(p['coverage']['required_concept_ids']),is_simulated=True,independent_task_success='NOT_MEASURED'))
 save(out/'config.json',config)
 paths=[*sorted((ROOT/'src/codecompass/learner').glob('*.py')),*sorted((ROOT/'src/codecompass/planner').glob('*.py')),ROOT/'scripts/A/run_d03.py',ROOT/'scripts/A/prepare_d03.py',ROOT/'scripts/B/b0.py',ROOT/'schemas/contracts-1.1.schema.json',*sorted((ROOT/'benchmarks/dev/D03').glob('*.json')),ROOT/'configs/A/D03_common.json',ROOT/'configs/A/D03_profiles.json',ROOT/'benchmarks/sources/boltons/snapshot.json',ROOT/config['documentation']['path']]
 frozen=[]
 for p in paths:
  relative=p.relative_to(ROOT);copy_path=out/'code_snapshot'/relative;copy_path.parent.mkdir(parents=True,exist_ok=True);copy_path.write_bytes(p.read_bytes())
  frozen.append({'path':relative.as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'frozen_copy':copy_path.relative_to(ROOT).as_posix()})
 save(out/'input_manifest.json',frozen)
 return {'paired_real_tasks':2,'simulated_profiles':2,'real_task_method_outputs':len(results),'boundary_checks':len(boundary),'all_expected_conditions_passed':True,
         'human_profiles':0,'formal_experiments':0,'diagnostics':'NOT_IMPLEMENTED','method':'B2-initial greedy; not beam/Ours or an optimality claim'}


def main():
 p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);a=p.parse_args()
 if not a.run_id.replace('-','').replace('_','').isalnum():p.error('Invalid run ID')
 out=ROOT/'experiments/A'/a.run_id;out.mkdir(parents=True,exist_ok=False);start=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.perf_counter()
 try:checks=execute(out,a.run_id);exit_code=0;error=None
 except Exception:
  checks={};exit_code=1;error=traceback.format_exc();(out/'failure.log').write_bytes(error.encode())
 git=os.environ.get('CODECOMPASS_GIT','git');base=subprocess.check_output([git,'rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 reg={'run_id':a.run_id,'task_id':'A-D03','evidence_type':'development_validation','is_simulated':True,'code_commit':None,'base_commit':base,'actor':'Codex Agent A','model_id':None,
      'machine':platform.node(),'python':sys.version,'started_at':start,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':time.perf_counter()-t,
      'command':sys.argv,'exit_code':exit_code,'error':error,'checks':checks,'api_cost':None,'metrics':None,'independent_review':'NOT_REVIEWED'}
 save(out/'registration.json',reg);print(json.dumps(reg,ensure_ascii=False,indent=2));return exit_code

if __name__=='__main__':raise SystemExit(main())
