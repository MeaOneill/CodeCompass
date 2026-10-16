import copy,itertools,random
from pathlib import Path
import pytest
from scripts.A.cases_d04 import unit,fixture,mechanism_cases
from codecompass.planner.core import greedy_plan,PlanningInputError
from codecompass.planner.beam import beam_plan,search_options
from codecompass.planner.exact import exact_plan
from codecompass.planner.comparison_validator import verify_result,verify_certificate

def solve(f,method,**kw):return method(f['request'],f['units'],f['state'],f['config'],**kw)

def audit(f,p,d):
    a=verify_result(f['request'],f['units'],p,d['gate'],d.get('certificate'));assert a['valid'],a
    return a

@pytest.mark.parametrize('f',mechanism_cases(),ids=lambda x:x['case_id'])
def test_mechanism_exact_and_strong_baseline(f):
    ep,ed=solve(f,exact_plan);audit(f,ep,ed);assert verify_certificate(f['request'],f['units'],ed['gate'],ed['certificate'])['valid']
    for method in (greedy_plan,beam_plan):
        p,d=solve(f,method);a=audit(f,p,d)
        if p['status']=='FEASIBLE':assert ep['status']=='FEASIBLE' and p['estimated_cost']+1e-9>=ep['estimated_cost']
        if ep['status']=='INFEASIBLE_PROVEN':assert not a['goal_complete']

def test_beam_recovers_greedy_miss_without_changing_baseline():
    f=next(x for x in mechanism_cases() if x['case_id']=='greedy_failure')
    gp,_=solve(f,greedy_plan);bp,bd=solve(f,beam_plan)
    assert gp['status']=='NO_FEASIBLE_FOUND' and gp['ordered_units']==['a']
    assert bp['status']=='FEASIBLE' and bp['ordered_units']==['b'] and bp['estimated_cost']==5 and not bd['optimality_claim']

def test_permutation_determinism_and_state_dedup():
    f=fixture('commute',[unit('a',['x']),unit('b',['y']),unit('c',['z'])],['x','y','z'],3)
    baseline=None;dedup=False
    for us in itertools.permutations(f['units']):
        q=copy.deepcopy(f);q['units']=list(us);q['request']['unit_ids']=[u['id'] for u in us]
        p,d=solve(q,beam_plan);audit(q,p,d);baseline=p if baseline is None else baseline;assert p==baseline
        dedup|=any(e['event']=='deduplicate' for e in d['events'])
    assert dedup

@pytest.mark.parametrize('key,value',[('beam_width',0),('beam_width',True),('candidate_limit',0),('max_expansions',0),('time_limit_seconds',-1),('time_limit_seconds',float('nan')),('unknown',1)])
def test_invalid_search_options(key,value):
    with pytest.raises(PlanningInputError):search_options({key:value})

def test_four_statuses_and_real_zero_wall_budget():
    feasible=fixture('f',[unit('a',['x'])],['x'],1)
    p,d=solve(feasible,beam_plan);assert p['status']=='FEASIBLE';audit(feasible,p,d)
    missing=fixture('m',[unit('a',['x'])],['missing'],1)
    p,d=solve(missing,beam_plan);assert p['status']=='NO_FEASIBLE_FOUND';audit(missing,p,d)
    p,d=solve(missing,exact_plan);assert p['status']=='INFEASIBLE_PROVEN';audit(missing,p,d)
    p,d=solve(feasible,beam_plan,options={'time_limit_seconds':0});assert p['status']=='TIMEOUT' and d['termination']=='WALL_CLOCK_TIMEOUT';audit(feasible,p,d)

def test_timeout_retains_feasible_incumbent_without_optimal_claim():
    f=fixture('clock',[unit('a',['x']),unit('b',['x'])],['x'],1)
    class Clock:
        calls=0
        def __call__(self):
            self.calls+=1
            return 0 if self.calls<7 else 2
    p,d=solve(f,beam_plan,options={'time_limit_seconds':1},clock=Clock())
    assert p['status']=='TIMEOUT' and not d['optimality_claim'];audit(f,p,d)

def test_candidate_and_beam_and_expansion_limits_logged():
    f=fixture('limit',[unit('a',['x'],2),unit('b',['x','y'],5),unit('c',['y'],4)],['x','y'],5)
    p,d=solve(f,beam_plan,options={'candidate_limit':1,'beam_width':1})
    assert d['truncated'] and any(e.get('candidate_truncation',{}).get('count',0)>0 for e in d['events'])
    assert p['status']=='NO_FEASIBLE_FOUND';audit(f,p,d)
    p,d=solve(f,beam_plan,options={'max_expansions':1});assert d['termination']=='EXPANSION_LIMIT' and not d['optimality_claim'];audit(f,p,d)
    p,d=solve(f,beam_plan,options={'beam_width':1});assert any(e.get('beam_truncation',{}).get('count',0)>0 for e in d['events'])

def test_proof_missing_tampered_or_reused_is_rejected():
    f=fixture('unreachable',[unit('a',['x'])],['missing'],1);p,d=solve(f,exact_plan)
    assert not verify_result(f['request'],f['units'],p,d['gate'])['valid']
    for key,value in [('complete',False),('input_hash','fake'),('reachable_masks',[]),('optimal_cost',0),('reachable_count',999),('unit_ids',[])]:
        c={**d['certificate'],key:value};assert not verify_result(f['request'],f['units'],p,d['gate'],c)['valid']
    g=copy.deepcopy(f);g['request']['budget']=2;assert not verify_result(g['request'],g['units'],p,d['gate'],d['certificate'])['valid']

def test_exact_cap_and_false_status_rejected():
    f=fixture('too_large',[unit(str(i),['x']) for i in range(13)],['x'],1)
    with pytest.raises(PlanningInputError):solve(f,exact_plan)
    f=fixture('f',[unit('a',['x'])],['x'],1);p,d=solve(f,beam_plan)
    for bad in [{**p,'estimated_cost':0},{**p,'ordered_units':['a','a']},{**p,'status':'INFEASIBLE_PROVEN','proof_path':'fake'},{**p,'request_id':'other'},{**p,'coverage':{**p['coverage'],'ratio':0}}]:
        assert not verify_result(f['request'],f['units'],bad,d['gate'])['valid']

def test_budget_epsilon_boundary():
    for budget,feasible in [(1-2e-9,False),(1-5e-10,True),(1,True)]:
        f=fixture('eps',[unit('a',['x'],1)],['x'],budget);p,d=solve(f,exact_plan);assert (p['status']=='FEASIBLE') is feasible;audit(f,p,d)

def permutation_oracle(f):
    # Exhaust all ordered subsets independently of bitmask DP/closure/beam.
    us={u['id']:u for u in f['units']};best=None
    for n in range(len(us)+1):
        for route in itertools.permutations(us,n):
            known=set();seen=set();cost=0;ok=True
            for uid in route:
                if any(e['hard'] and e['unit_id'] not in seen and not set(us[e['unit_id']]['concept_ids'])<=known for e in us[uid]['prerequisites']):ok=False;break
                seen.add(uid);known.update(us[uid]['concept_ids']);cost+=us[uid]['base_cost']
            if ok and cost<=f['request']['budget']+1e-9 and set(f['request']['target_concept_ids'])<=known:best=cost if best is None else min(best,cost)
    return best

def test_seeded_graphs_against_independent_permutation_oracle():
    rng=random.Random(41018)
    for i in range(45):
        n=rng.randint(1,5);us=[unit(str(j),[rng.choice(['x','y','z'])],rng.randint(0,4),[str(k) for k in range(n) if k!=j and rng.random()<.13]) for j in range(n)]
        f=fixture('random'+str(i),us,['x','y'],rng.randint(0,10));p,d=solve(f,exact_plan);audit(f,p,d);optimal=permutation_oracle(f)
        assert d['certificate']['optimal_cost']==optimal
        p,d=solve(f,beam_plan);audit(f,p,d)
        if p['status']=='FEASIBLE':assert optimal is not None and p['estimated_cost']>=optimal

def test_new_service_same_real_pool_and_old_service_stays_intact():
    import json
    from scripts.A.run_d03 import load,make_request,make_profile
    from codecompass.planner.search_service import solve_request
    root=Path(__file__).resolve().parents[2];task=load('benchmarks/dev/D03/task_001.json');units=[u for u in load('benchmarks/dev/D03/units.json') if u['id'] in task['learning_unit_ids']];config=load('configs/A/D03_common.json');profile=load('configs/A/D03_profiles.json')['profiles'][0];state=make_profile(profile,task['snapshot_id']);req=make_request(task,units,state,config,'D04-real-service')
    for method in ('B2','beam','exact'):
        p,d=solve_request(root,req,units,state,config,method=method);assert d['replay_audit']['valid']
    bad=copy.deepcopy(units);bad[0]['source_spans'][0]['start_line']+=1
    with pytest.raises(ValueError):solve_request(root,req,bad,state,config)

def test_optional_certification_does_not_substitute_an_exact_feasible_witness(monkeypatch):
    # Compact structural fixtures bypass only schema/source boundary in this test;
    # direct functions above test proof/heuristic separation on these fixtures.
    f=fixture('known_feasible',[unit('a',['x'],2),unit('b',['x','y'],5),unit('c',['y'],4)],['x','y'],5)
    p,d=solve(f,beam_plan,options={'candidate_limit':1,'beam_width':1});ep,ed=solve(f,exact_plan)
    assert p['status']=='NO_FEASIBLE_FOUND' and ep['status']=='FEASIBLE'


def test_feasible_certificate_route_cannot_be_replaced_by_fake_route():
    f=fixture('cert',[unit('a',['x'])],['x'],1);p,d=solve(f,exact_plan)
    for route in [[],['unknown'],['a','a']]:
        bad={**d['certificate'],'optimal_route':route}
        assert not verify_certificate(f['request'],f['units'],d['gate'],bad)['valid']


def test_service_can_certify_only_complete_exact_infeasibility():
    from codecompass.planner.search_service import solve_request
    root=Path(__file__).resolve().parents[2]
    f=fixture('certified',[unit('a',['x'])],['missing'],1)
    p,d=solve_request(root,f['request'],f['units'],f['state'],f['config'],certify_small=True)
    assert p['status']=='INFEASIBLE_PROVEN' and d['replay_audit']['valid']
    f=fixture('not_proven',[unit('a',['x'],2),unit('b',['x','y'],5),unit('c',['y'],4)],['x','y'],5)
    p,d=solve_request(root,f['request'],f['units'],f['state'],f['config'],certify_small=True,options={'beam_width':1,'candidate_limit':1})
    assert p['status']=='NO_FEASIBLE_FOUND' and d['exact_feasible_witness']['status']=='FEASIBLE'
