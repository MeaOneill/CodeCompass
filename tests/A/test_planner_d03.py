import copy
import math
import pytest
from codecompass.learner import initial_state, update_evidence, planning_rows, mastery_gate, beta_quantile
from codecompass.planner import greedy_plan, reverse_closure, validate_units, PlanningInputError, ClosureCycle, check_plan

CONFIG={'version':'fixture-v1','threshold':.7,'quantile':.1}

def evidence(state,concept,item,outcome='pass',**kw):
    return {'schema_version':'1.0.0','object_type':'LearnerEvidence','is_fixture':state['is_simulated'],'evidence_id':'e_'+concept+'_'+item,'pseudonymous_user_id':state['pseudonymous_user_id'],'concept_id':concept,'item_id':item,'outcome':outcome,'timestamp':'2026-10-16T20:00:00+08:00','project':'fixture_snapshot','evidence_type':'independent_quiz','attempt_id':'attempt_'+item,'independent':True,**kw}

def state_with(concepts=(),count=10):
    state=initial_state('synthetic_user',is_simulated=True)
    for c in concepts:
        for i in range(count):state,_=update_evidence(state,evidence(state,c,c+str(i)),allow_simulated=True)
    return state

def unit(uid,concepts,cost=1,deps=(),hard=True):
    return {'schema_version':'1.0.0','object_type':'LearningUnit','is_fixture':True,'id':uid,'concept_ids':list(concepts),'source_spans':[],
            'base_cost':cost,'cost_unit':'proxy_cost','prerequisites':[{'unit_id':p,'relation_type':'teaching_prerequisite','hard':hard,'provenance':{'kind':'fixture','review_status':'approved','reviewer':'SYNTHETIC_REVIEW_NOT_A_PERSON','evidence':['fixture-only:structural-constraint']}} for p in deps]}

def request(units,goals,budget=100,state=None):
    state=state_with() if state is None else state
    return {'schema_version':'1.0.0','object_type':'PlanningRequest','is_fixture':True,'request_id':'fixture_request','snapshot_id':'fixture_snapshot','task_id':'fixture_task','learner_state':planning_rows(state,'fixture_snapshot',allow_simulated=True),'budget':budget,'cost_unit':'proxy_cost','config_version':CONFIG['version'],'target_concept_ids':list(goals),'unit_ids':[u['id'] for u in units],'prior_plan_id':None}

def run(units,goals,budget=100,state=None):
    state=state_with() if state is None else state
    req=request(units,goals,budget,state);plan,detail=greedy_plan(req,units,state,CONFIG)
    audit=check_plan(req,units,plan,detail['gate']);assert audit['structurally_valid'],audit
    return req,plan,detail

@pytest.mark.parametrize('a,b,q,expected',[(1,1,.1,.1),(11,1,.1,.1**(1/11)),(1,11,.1,1-.9**(1/11)),(2,2,.5,.5),(10,10,.5,.5)])
def test_beta_against_closed_forms(a,b,q,expected):
    assert beta_quantile(a,b,q)==pytest.approx(expected,abs=1e-12)

@pytest.mark.parametrize('a,b,q',[(0,1,.1),(1.5,1,.1),(True,1,.1),(1,1,0),(1,1,float('nan')),(2001,2,.1)])
def test_bad_beta_inputs_rejected(a,b,q):
    with pytest.raises(ValueError):beta_quantile(a,b,q)


def test_update_pure_duplicates_conflicts_and_failures():
    state=initial_state('real_user');before=copy.deepcopy(state);e=evidence(state,'x','q1')
    after,decision=update_evidence(state,e);assert decision=='ACCEPTED' and state==before
    same,decision=update_evidence(after,copy.deepcopy(e));assert decision=='DUPLICATE_EVIDENCE' and same==after
    repeated={**e,'evidence_id':'new_id','outcome':'fail'}
    same,decision=update_evidence(after,repeated);assert decision=='DUPLICATE_ITEM' and same==after
    with pytest.raises(ValueError):update_evidence(after,{**e,'outcome':'fail'})
    after,_=update_evidence(after,evidence(state,'x','q2','fail'))
    row=planning_rows(after,'fixture_snapshot')[0];assert (row['alpha'],row['beta'])==(2,2)


def test_reading_selfreport_unscored_not_mastery():
    s=initial_state('real_user')
    for e in [evidence(s,'x','q1',independent=False),evidence(s,'x','q2',evidence_type='self_report'),evidence(s,'x','q3',outcome='unscored')]:
        updated,d=update_evidence(s,e);assert updated==s and d.startswith('IGNORED')
    gate=mastery_gate(s,'fixture_snapshot',['x']);assert gate['x']['lower_bound'] is None and not gate['x']['mastered']


def test_simulation_user_project_and_timestamp_boundaries():
    s=state_with(['x'])
    with pytest.raises(ValueError):planning_rows(s,'fixture_snapshot')
    real=initial_state('real_user')
    with pytest.raises(ValueError):update_evidence(real,evidence(real,'x','q',is_fixture=True),allow_simulated=True)
    with pytest.raises(ValueError):update_evidence(real,evidence(real,'x','q',pseudonymous_user_id='other'))
    with pytest.raises(ValueError):update_evidence(real,evidence(real,'x','q',timestamp='2026-10-16'))
    assert not mastery_gate(s,'different_project',['x'],allow_simulated=True)['x']['mastered']


def test_one_item_does_not_prove_mastery_and_ten_can_pass_model_gate():
    assert not mastery_gate(state_with(['x'],1),'fixture_snapshot',['x'],allow_simulated=True)['x']['mastered']
    assert mastery_gate(state_with(['x'],10),'fixture_snapshot',['x'],allow_simulated=True)['x']['mastered']


def test_shared_prerequisite_charged_once_and_before_targets():
    units=[unit('s',['foundation'],1),unit('a',['x'],2,['s']),unit('b',['y'],2,['s'])]
    req,p,d=run(units,['x','y'],5)
    assert p['status']=='FEASIBLE' and p['estimated_cost']==5 and p['ordered_units'].count('s')==1
    assert p['ordered_units'].index('s')<p['ordered_units'].index('a') and p['ordered_units'].index('s')<p['ordered_units'].index('b')


def test_mastered_prerequisite_skip_is_replayed_consistently():
    units=[unit('s',['foundation'],5),unit('a',['x'],2,['s'])]
    _,p,_=run(units,['x'],2,state_with(['foundation']))
    assert p['ordered_units']==['a'] and p['estimated_cost']==2
    assert any(r['evidence_ids'] for r in p['reason_trace'])


def test_alternative_material_selects_incremental_cost_not_lexical_rank():
    units=[unit('a_expensive',['x'],8),unit('z_cheap',['x'],2)]
    _,p,_=run(units,['x'],2);assert p['ordered_units']==['z_cheap']


def test_partial_mastery_does_not_skip_multi_concept_unit():
    _,p,_=run([unit('u',['x','y'],3)],['x','y'],3,state_with(['x']))
    assert p['ordered_units']==['u']


def test_cycles_preserved_and_alternative_can_avoid_them():
    units=[unit('a',['x'],1,['b']),unit('b',['y'],1,['a'])]
    _,p,d=run(units,['x'],100);assert p['status']=='NO_FEASIBLE_FOUND' and any('cycle' in s for s in p['unmet_constraints'])
    assert p['proof_path'] is None
    _,p,_=run(units+[unit('z',['x'],5)],['x'],5);assert p['ordered_units']==['z']


def test_budget_unreachable_unknown_and_zero_budget():
    _,p,_=run([unit('u',['x'],3)],['x'],2);assert p['status']=='NO_FEASIBLE_FOUND' and p['coverage']['ratio']==0
    _,p,_=run([unit('u',['x'],3)],['missing'],100);assert any('no candidate' in x for x in p['unmet_constraints'])
    _,p,_=run([unit('u',['x'],3)],['x'],0,state_with(['x']));assert p['status']=='FEASIBLE' and p['ordered_units']==[]
    _,p,_=run([],[],0);assert p['coverage']['ratio'] is None
    _,p,_=run([unit('u',['x'],0)],['x'],0);assert p['status']=='FEASIBLE'

@pytest.mark.parametrize('bad',[None,-1,True,float('nan'),float('inf')])
def test_unknown_negative_or_nonfinite_cost_never_zero(bad):
    with pytest.raises(PlanningInputError):run([unit('u',['x'],bad)],['x'])

@pytest.mark.parametrize('bad',[-1,True,float('nan'),float('inf')])
def test_invalid_budgets(bad):
    with pytest.raises(PlanningInputError):run([unit('u',['x'])],['x'],bad)


def test_soft_edges_do_not_become_hard_and_unapproved_hard_rejected():
    units=[unit('a',['x'],1,['b'],False),unit('b',['y'],1,['a'],False)]
    _,p,_=run(units,['x'],1);assert p['ordered_units']==['a']
    units[0]['prerequisites'][0]['hard']=True;units[0]['prerequisites'][0]['provenance']['review_status']='pending'
    with pytest.raises(PlanningInputError):run(units,['x'])


def test_forged_aggregate_dangling_duplicate_and_snapshot_rejected():
    us=[unit('u',['x'])];s=state_with();req=request(us,['x']);req['learner_state']=[{'concept_id':'x','alpha':100}]
    with pytest.raises(PlanningInputError):greedy_plan(req,us,s,CONFIG)
    with pytest.raises(PlanningInputError):run(us+us,['x'])
    with pytest.raises(PlanningInputError):run([unit('u',['x'],1,['missing'])],['x'])
    us[0]['is_fixture']=False;us[0]['source_spans']=[{'snapshot_id':'wrong'}]
    with pytest.raises(PlanningInputError):run(us,['x'])


def test_known_feasible_but_greedy_can_fail_no_global_claim():
    us=[unit('a',['x'],2),unit('b',['x','y'],5),unit('c',['y'],4)]
    req,p,d=run(us,['x','y'],5)
    assert p['status']=='NO_FEASIBLE_FOUND' and p['ordered_units']==['a']
    witness=copy.deepcopy(p);witness.update(status='FEASIBLE',ordered_units=['b'],estimated_cost=5,unmet_constraints=[])
    witness['coverage'].update(covered_concept_ids=['x','y'],ratio=1)
    assert check_plan(req,us,witness,d['gate'])['structurally_valid']


def test_checker_rejects_tampered_paths_costs_coverage_status():
    us=[unit('s',['base']),unit('u',['x'],1,['s'])];req,p,d=run(us,['x'])
    bads=[]
    bad=copy.deepcopy(p);bad['ordered_units'].reverse();bads.append(bad)
    bad=copy.deepcopy(p);bad['ordered_units'].append('u');bads.append(bad)
    bad=copy.deepcopy(p);bad['estimated_cost']=0;bads.append(bad)
    bad=copy.deepcopy(p);bad['coverage']['ratio']=0;bads.append(bad)
    bad=copy.deepcopy(p);bad['status']='INFEASIBLE_PROVEN';bads.append(bad)
    for bad in bads:assert not check_plan(req,us,bad,d['gate'])['structurally_valid']

def test_many_tiny_graphs_against_exhaustive_feasibility_oracle():
    from itertools import product,combinations
    # An independent subset oracle, no prerequisite graph or greedy objective reuse.
    choices=[(['x'],1),(['x'],3),(['y'],1),(['y'],3),(['x','y'],1),(['x','y'],3)]
    for material_options in product(choices,repeat=3):
        us=[unit(str(i),concepts,cost) for i,(concepts,cost) in enumerate(material_options)]
        for budget in range(7):
            _,p,_=run(us,['x','y'],budget)
            exists=any(sum(us[i]['base_cost'] for i in subset)<=budget and {'x','y'}<={c for i in subset for c in us[i]['concept_ids']} for k in range(4) for subset in combinations(range(3),k))
            if p['status']=='FEASIBLE':assert exists
            if not exists:assert p['status']=='NO_FEASIBLE_FOUND'


def test_versioned_contract_service_and_new_task_origin():
    from pathlib import Path
    import json
    from jsonschema import Draft202012Validator
    from codecompass.planner import plan_request
    from scripts.A.run_d03 import make_profile,make_request
    root=Path(__file__).resolve().parents[2]
    read=lambda p:json.loads((root/p).read_text(encoding='utf-8'))
    task=read('benchmarks/dev/D03/task_002.json');config=read('configs/A/D03_common.json')
    units=[u for u in read('benchmarks/dev/D03/units.json') if u['id'] in task['learning_unit_ids']]
    state=make_profile(read('configs/A/D03_profiles.json')['profiles'][0],task['snapshot_id'])
    req=make_request(task,units,state,config,'service-fixture')
    p,d=plan_request(root,req,units,state,config)
    assert p['status']=='FEASIBLE' and d['replay_audit']['structurally_valid']
    assert Draft202012Validator(read('schemas/contracts-1.1.schema.json')).is_valid(task)
    assert not Draft202012Validator(read('schemas/contracts.schema.json')).is_valid(task)
    old=read('benchmarks/dev/task_001_units.json');assert all(u['base_cost'] is None for u in old)


def test_fixture_material_cannot_silently_become_real_plan():
    us=[unit('u',['x'])];s=initial_state('real_user')
    req=request(us,['x']);req.update(is_fixture=False,learner_state=[])
    with pytest.raises(PlanningInputError):greedy_plan(req,us,s,CONFIG)

def test_empty_identity_and_forged_source_span_fail_closed():
    from codecompass.learner import validate_state
    for bad in [None,'']:
        s=initial_state('test');s['pseudonymous_user_id']=bad
        with pytest.raises(ValueError):validate_state(s)
    from pathlib import Path
    import json
    from scripts.A.run_d03 import make_profile,make_request
    from codecompass.planner import plan_request
    root=Path(__file__).resolve().parents[2];read=lambda p:json.loads((root/p).read_text(encoding='utf-8'))
    task=read('benchmarks/dev/D03/task_002.json');config=read('configs/A/D03_common.json')
    us=[u for u in read('benchmarks/dev/D03/units.json') if u['id'] in task['learning_unit_ids']]
    s=make_profile(read('configs/A/D03_profiles.json')['profiles'][0],task['snapshot_id']);req=make_request(task,us,s,config,'source-mutation')
    us[0]['source_spans'][0]['content_hash']='0'*64
    with pytest.raises(ValueError):plan_request(root,req,us,s,config)


@pytest.mark.parametrize("budget",["-1","nan","inf","-inf"])
def test_live_demo_rejects_invalid_budget_without_traceback(monkeypatch,capsys,budget):
    from scripts.A import demo_d03
    monkeypatch.setattr("sys.argv",["demo_d03.py","--budget="+budget])
    assert demo_d03.main()==2
    output=capsys.readouterr()
    assert "预算必须是有限非负数" in output.out and not output.err


def test_live_demo_reports_contract_failure_without_ledger_dump(monkeypatch,capsys):
    from scripts.A import demo_d03
    from jsonschema.exceptions import ValidationError
    def reject(*args,**kwargs):raise ValidationError("private request body")
    monkeypatch.setattr("sys.argv",["demo_d03.py"])
    monkeypatch.setattr(demo_d03,"plan_request",reject)
    assert demo_d03.main()==2
    output=capsys.readouterr()
    assert "不符合版本契约" in output.out and "private request" not in output.out and not output.err
