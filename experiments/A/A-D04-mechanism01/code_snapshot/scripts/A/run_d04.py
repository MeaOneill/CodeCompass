"""Reproducible mechanism-only comparison; never measures human outcomes."""
import argparse,csv,datetime,hashlib,json,os,platform,subprocess,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT))
from scripts.A.cases_d04 import mechanism_cases,CONFIG
from scripts.A.run_d03 import load,make_request,make_profile
from codecompass.planner.search_service import solve_request
from codecompass.planner.comparison_validator import verify_certificate
from codecompass.planner.search_common import canonical_hash

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode())

def execute(out,run_id):
    rows=[];cases=mechanism_cases();common=load('configs/A/D03_common.json')
    for tid in ('task_001','task_002'):
        task=load('benchmarks/dev/D03/'+tid+'.json');units=[u for u in load('benchmarks/dev/D03/units.json') if u['id'] in task['learning_unit_ids']]
        for profile in load('configs/A/D03_profiles.json')['profiles']:
            name=tid+'-'+profile['id'];state=make_profile(profile,task['snapshot_id']);req=make_request(task,units,state,common,'D04-'+name)
            cases.append({'case_id':name,'is_simulated':True,'units':units,'request':req,'state':state,'config':common,'real_source_task':True})
    for f in cases:
        name=f['case_id'];folder=out/'cases'/name;save(folder/'input.json',f);results={}
        for method in ('exact','B2','beam'):
            p,d=solve_request(ROOT,f['request'],f['units'],f['state'],f['config'],method=method)
            if method=='exact':
                cert=verify_certificate(f['request'],f['units'],d['gate'],d['certificate']);assert cert['valid'];save(folder/'certificate.json',d['certificate'])
            save(folder/(method+'.json'),{'result':p,'details':d});results[method]=(p,d)
        optimum=results['exact'][1]['certificate']['optimal_cost']
        for method,(p,d) in results.items():
            candidate_cost=p['estimated_cost'] if p['status']=='FEASIBLE' else None
            gap=candidate_cost-optimum if candidate_cost is not None and optimum is not None else None
            assert candidate_cost is None or candidate_cost+1e-9>=optimum
            rows.append({'case_id':name,'method':method,'units':len(f['units']),'source_kind':'fixed_real_task' if f.get('real_source_task') else 'synthetic_structure','profile_is_simulated':True,'status':p['status'],'route':p['ordered_units'],'partial_proxy_cost':p['estimated_cost'],'feasible_proxy_cost':candidate_cost,'exact_proxy_cost':optimum,'additive_cost_gap':gap,'goal_complete':d['replay_audit']['goal_complete'],'optimality_claim':method=='exact' and p['status']=='FEASIBLE','human_task_success':None,'human_elapsed_minutes':None})
    # Actual invocations for bounded misses, zero wall budget, and certified failure.
    by_name={c['case_id']:c for c in cases};status_specs=[('FEASIBLE','cost_gap',{},False),('NO_FEASIBLE_FOUND','greedy_failure',{'beam_width':1,'candidate_limit':1},True),('INFEASIBLE_PROVEN','unreachable',{},True),('TIMEOUT','cost_gap',{'time_limit_seconds':0.0},False)]
    triggers=[]
    for expected,name,options,certify in status_specs:
        f=by_name[name];p,d=solve_request(ROOT,f['request'],f['units'],f['state'],f['config'],options=options,certify_small=certify);assert p['status']==expected
        save(out/'status_examples'/expected/'input.json',f);save(out/'status_examples'/expected/'output.json',{'result':p,'details':d})
        if d.get('certificate'):save(out/'status_examples'/expected/'certificate.json',d['certificate'])
        triggers.append({'expected':expected,'actual':p['status'],'options':options,'certify_small':certify,'passed':True})
    widths=[]
    for name in ('greedy_failure','cost_gap','unique_chain','twelve_units'):
        f=by_name[name]
        for width in (1,4,16,32):
            p,d=solve_request(ROOT,f['request'],f['units'],f['state'],f['config'],options={'beam_width':width});save(out/'widths'/name/(str(width)+'.json'),{'result':p,'details':d});widths.append({'case_id':name,'beam_width':width,'status':p['status'],'cost_if_feasible':p['estimated_cost'] if p['status']=='FEASIBLE' else None,'truncated':d['truncated'],'optimality_claim':False})
    save(out/'summary.json',{'run_id':run_id,'kind':'mechanism_correctness_only','comparisons':rows,'status_examples':triggers,'width_sensitivity':widths,'human_profiles':0,'formal_study_ready':False,'diagnostics':'NOT_IMPLEMENTED','learning_effect':'NOT_MEASURED','B2_policy':'unchanged A-D03 closure gain/cost greedy','budget_epsilon':1e-9,'real_teaching_hard_edges':0})
    with (out/'comparison.csv').open('w',encoding='utf-8',newline='') as stream:
        fields=[k for k in rows[0] if k!='route'];writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for row in rows:writer.writerow({k:('NOT_MEASURED' if row[k] is None else row[k]) for k in fields})
    # Freeze code/input bytes; source changed after this run must trigger audit failure.
    files=[*sorted((ROOT/'src/codecompass/planner').glob('*.py')),*sorted((ROOT/'src/codecompass/learner').glob('*.py')),ROOT/'scripts/A/cases_d04.py',ROOT/'scripts/A/run_d04.py',ROOT/'scripts/A/run_d03.py',ROOT/'tests/A/test_search_d04.py',ROOT/'schemas/contracts-1.1.schema.json',*sorted((ROOT/'configs/A').glob('*.json')),*sorted((ROOT/'benchmarks/dev/D03').glob('*.json')),ROOT/'benchmarks/sources/boltons/snapshot.json']
    manifest=[]
    for p in files:
        rel=p.relative_to(ROOT);copy=out/'code_snapshot'/rel;copy.parent.mkdir(parents=True,exist_ok=True);copy.write_bytes(p.read_bytes());manifest.append({'path':rel.as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'frozen_copy':copy.relative_to(ROOT).as_posix()})
    save(out/'input_manifest.json',manifest)
    return {'comparisons':len(rows),'synthetic_graphs':len(mechanism_cases()),'real_tasks':2,'simulated_profiles':2,'status_examples':4,'width_runs':len(widths)}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-id',required=True);args=parser.parse_args()
    if not args.run_id.replace('-','').replace('_','').isalnum():parser.error('Unsafe run ID')
    out=ROOT/'experiments/A'/args.run_id;out.mkdir(parents=True,exist_ok=False);started=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.perf_counter()
    try:counts=execute(out,args.run_id);code=0;error=None
    except Exception:counts={};code=1;error=traceback.format_exc();(out/'failure.log').write_bytes(error.encode())
    git=os.environ.get('CODECOMPASS_GIT','git');base=subprocess.check_output([git,'rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    reg={'run_id':args.run_id,'task_id':'A-D04','machine':platform.node(),'executor':'Codex Agent A','model_id':None,'started_at':started,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':time.perf_counter()-t,'command':['python',*sys.argv],'exit_code':code,'error':error,'code_commit':None,'base_commit':base,'is_simulated':True,'human_profiles':0,'formal_study_ready':False,'counts':counts}
    save(out/'registration.json',reg);print(json.dumps(reg,ensure_ascii=False,indent=2));return code
if __name__=='__main__':raise SystemExit(main())
